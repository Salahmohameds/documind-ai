"""OCI Object Storage writer — required for anything beyond a single pod.

The local backend depends on a filesystem the pod happens to have mounted,
which cannot be shared across document-service replicas and cannot be read
by processing-service's pods (which read the documents bucket directly, see
services/processing-service/app/storage/oci_object_storage.py). Object
Storage is reachable from every pod on every node, so it is what makes the
document-upload path and the processing pipeline actually connect once this
runs in Kubernetes rather than docker-compose.

The ``oci`` SDK is an **optional dependency**, imported on first use rather
than at module import — same pattern as processing-service's reader and
ai-service's OCI Generative AI adapter: the default image and the whole test
suite stay free of it. ``requirements-oci.txt`` is installed via
``--build-arg INSTALL_OCI=true``.

Authentication is never a credential in an env var:

* ``workload``  — OKE workload identity. The pod's service account is mapped
  to an IAM dynamic group with a policy allowing object writes on the
  documents/processed buckets. Nothing to rotate, nothing to leak. This is
  the production mode.
* ``instance``  — instance principal, for a plain VM.
* ``config``    — ``~/.oci/config``, local development only.
"""

from __future__ import annotations

import logging
import threading

from fastapi import UploadFile

from app.config import settings
from app.errors import InvalidDocumentError, StorageUnavailableError, UploadTooLargeError
from app.storage.base import StoredObject

logger = logging.getLogger(settings.service_name)

_CHUNK_SIZE = 1024 * 1024
_PDF_HEADER_SCAN_BYTES = 1024


class OCIObjectStorage:
    """Implements the DocumentStorage protocol (see app/storage/base.py) against
    an OCI Object Storage bucket."""

    def __init__(
        self,
        *,
        bucket_name: str,
        namespace: str = "",
        region: str = "",
        auth_mode: str = "workload",
    ) -> None:
        self._bucket_name = bucket_name
        self._namespace = namespace
        self._region = region
        self._auth_mode = auth_mode
        self._client = None
        # Built lazily so importing this module (or constructing it in a test
        # that never calls save_pdf) never requires the OCI SDK or network.
        self._lock = threading.Lock()

    # -- client construction --------------------------------------------------
    def _build_client(self):
        import oci  # noqa: PLC0415 — optional dependency, imported on demand

        if self._auth_mode == "workload":
            signer = oci.auth.signers.get_oke_workload_identity_resource_principal_signer()
            config = {"region": self._region} if self._region else {}
            return oci.object_storage.ObjectStorageClient(config, signer=signer)

        if self._auth_mode == "instance":
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            config = {"region": self._region} if self._region else {}
            return oci.object_storage.ObjectStorageClient(config, signer=signer)

        # config: local development only.
        config = oci.config.from_file()
        if self._region:
            config["region"] = self._region
        return oci.object_storage.ObjectStorageClient(config)

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        self._client = self._build_client()
                        if not self._namespace:
                            self._namespace = self._client.get_namespace().data
                    except ImportError as exc:
                        raise StorageUnavailableError(
                            "STORAGE_TYPE=oci_object_storage but the 'oci' SDK "
                            "is not installed. Build the image with "
                            "--build-arg INSTALL_OCI=true."
                        ) from exc
                    except Exception as exc:
                        raise StorageUnavailableError(
                            f"Could not initialise the Object Storage client: {exc}"
                        ) from exc
        return self._client

    # -- DocumentStorage protocol ---------------------------------------------
    async def save_pdf(
        self, upload: UploadFile, storage_key: str, max_bytes: int
    ) -> StoredObject:
        client = self._get_client()

        # Buffered in memory, not streamed straight to put_object: OCI's
        # put_object needs a Content-Length up front for a single-part
        # upload, and max_bytes (25 MB default) is small enough that holding
        # one upload in memory per in-flight request is cheap. A multipart
        # upload would remove this cap if larger documents are ever allowed.
        body = bytearray()
        try:
            while chunk := await upload.read(_CHUNK_SIZE):
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise UploadTooLargeError("A document may not exceed 25 MB.")
        finally:
            await upload.close()

        if b"%PDF-" not in bytes(body[:_PDF_HEADER_SCAN_BYTES]):
            raise InvalidDocumentError("The uploaded file is not a valid PDF document.")

        try:
            client.put_object(
                namespace_name=self._namespace,
                bucket_name=self._bucket_name,
                object_name=storage_key,
                put_object_body=bytes(body),
                content_type="application/pdf",
            )
        except Exception as exc:
            raise StorageUnavailableError(
                f"Object Storage write failed for {storage_key!r}: {exc}"
            ) from exc

        return StoredObject(storage_key=storage_key, size_bytes=len(body))

    def delete(self, storage_key: str) -> None:
        client = self._get_client()
        try:
            client.delete_object(
                namespace_name=self._namespace,
                bucket_name=self._bucket_name,
                object_name=storage_key,
            )
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status == 404:
                # Best-effort cleanup — already gone is a success, not an error.
                return
            logger.warning("Object Storage delete failed for %r: %s", storage_key, exc)

    def size_bytes(self, storage_key: str) -> int | None:
        client = self._get_client()
        try:
            response = client.head_object(
                namespace_name=self._namespace,
                bucket_name=self._bucket_name,
                object_name=storage_key,
            )
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status == 404:
                return None
            raise StorageUnavailableError(
                f"Object Storage head failed for {storage_key!r}: {exc}"
            ) from exc
        declared = response.headers.get("Content-Length") if response.headers else None
        return int(declared) if declared is not None else None

    def health_check(self) -> None:
        client = self._get_client()
        try:
            client.get_bucket(
                namespace_name=self._namespace, bucket_name=self._bucket_name
            )
        except Exception as exc:
            raise StorageUnavailableError(
                f"Bucket {self._bucket_name!r} is not reachable: {exc}"
            ) from exc

"""OCI Object Storage reader — the production backend.

This is what makes the worker genuinely horizontally scalable. The local
backend depends on a filesystem the pod happens to have mounted; Object Storage
is reachable from every pod on every node, so `replicas: 10` under the HPA is a
number rather than a hope.

The ``oci`` SDK is an **optional dependency**, imported on first use rather than
at module import. Same pattern as
``services/ai-service/app/adapters/oci_genai.py``: the default image and the
whole test suite stay free of it, and a developer with no OCI account can still
run and test everything. ``requirements-oci.txt`` is installed via
``--build-arg INSTALL_OCI=true``.

Authentication is never a credential in an env var:

* ``workload``  — OKE workload identity. The pod's service account is mapped to
  an IAM dynamic group with a policy allowing reads on the bucket. Nothing to
  rotate, nothing to leak. This is the production mode.
* ``instance``  — instance principal, for a plain VM.
* ``config``    — ``~/.oci/config``, local development only.
"""

from __future__ import annotations

import logging
import threading

from app.config import settings
from app.errors import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    StorageUnavailableError,
)

logger = logging.getLogger(settings.service_name)


class OCIObjectStorageReader:
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
        # The client is built lazily on the first job. Two jobs starting at
        # once in the same pod would otherwise each build one.
        self._lock = threading.Lock()

    # -- client construction ------------------------------------------------
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
                        # A configuration error, not a transient one: retrying
                        # will not install the SDK. Surfaced loudly because it
                        # means the image was built without INSTALL_OCI=true.
                        raise StorageUnavailableError(
                            "STORAGE_TYPE=oci but the 'oci' SDK is not installed. "
                            "Build the image with --build-arg INSTALL_OCI=true."
                        ) from exc
                    except Exception as exc:
                        raise StorageUnavailableError(
                            f"Could not initialise the Object Storage client: {exc}"
                        ) from exc
        return self._client

    # -- reader contract ----------------------------------------------------
    def read(self, storage_key: str, max_bytes: int) -> bytes:
        client = self._get_client()

        try:
            response = client.get_object(
                namespace_name=self._namespace,
                bucket_name=self._bucket_name,
                object_name=storage_key,
            )
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status == 404:
                raise DocumentNotFoundError(
                    f"No object {storage_key!r} in bucket {self._bucket_name!r}"
                ) from exc
            # 401/403 are usually a broken IAM policy — a configuration
            # problem. But retrying is harmless and an expired token does
            # resolve itself, so these stay retryable.
            raise StorageUnavailableError(
                f"Object Storage read failed for {storage_key!r}: {exc}"
            ) from exc

        # Trust Content-Length when present so an oversized object is rejected
        # before its bytes are pulled into the pod.
        declared = response.headers.get("Content-Length") if response.headers else None
        if declared is not None and int(declared) > max_bytes:
            raise DocumentTooLargeError(
                f"Object {storage_key!r} is {declared} bytes, over the "
                f"{max_bytes}-byte limit"
            )

        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
                total += len(chunk)
                # Enforced during streaming too: Content-Length can be absent
                # or wrong, and the limit exists to protect the pod's memory.
                if total > max_bytes:
                    raise DocumentTooLargeError(
                        f"Object {storage_key!r} exceeds the {max_bytes}-byte limit"
                    )
                chunks.append(chunk)
        except DocumentTooLargeError:
            raise
        except Exception as exc:
            raise StorageUnavailableError(
                f"Object Storage stream failed for {storage_key!r}: {exc}"
            ) from exc

        return b"".join(chunks)

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

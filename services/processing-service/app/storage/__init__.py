"""Storage backend selection."""

from __future__ import annotations

from app.config import settings
from app.storage.base import DocumentReader
from app.storage.local import LocalDocumentReader

__all__ = ["DocumentReader", "build_reader"]


def build_reader() -> DocumentReader:
    """Construct the reader named by ``STORAGE_TYPE``.

    The OCI module is imported inside the branch so the default deployment
    never touches the optional SDK.
    """
    if settings.storage_type == "oci":
        from app.storage.oci_object_storage import (  # noqa: PLC0415
            OCIObjectStorageReader,
        )

        return OCIObjectStorageReader(
            bucket_name=settings.oci_bucket_name,
            namespace=settings.oci_namespace,
            region=settings.oci_region,
            auth_mode=settings.oci_auth_mode,
        )

    return LocalDocumentReader(settings.storage_dir)

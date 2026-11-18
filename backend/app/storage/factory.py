from app.core.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage

_storage_instance: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        settings = get_settings()
        if settings.STORAGE_BACKEND == "s3":
            _storage_instance = S3Storage(
                endpoint_url=settings.S3_ENDPOINT_URL,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                bucket=settings.S3_BUCKET,
                region=settings.S3_REGION,
            )
        else:
            _storage_instance = LocalStorage(settings.LOCAL_STORAGE_PATH)
    return _storage_instance


def set_storage_override(storage: StorageBackend | None) -> None:
    global _storage_instance
    _storage_instance = storage

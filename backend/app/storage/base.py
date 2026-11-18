from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def put_file(self, key: str, file_path: Path, content_type: str = "application/octet-stream") -> None:
        raise NotImplementedError

    @abstractmethod
    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        raise NotImplementedError

    @abstractmethod
    def download_file(self, key: str, dest_path: Path) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def get_size(self, key: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def iter_range(
        self, key: str, start: int, end: int, chunk_size: int = 262144
    ) -> Iterator[bytes]:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> bool:
        raise NotImplementedError

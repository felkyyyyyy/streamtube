from collections.abc import Iterator
from pathlib import Path
import shutil

from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Filesystem storage backend with path-traversal protection (for local dev & pytest)."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        clean_key = key.lstrip("/").replace("\\", "/")
        target = (self.root / clean_key).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Invalid storage key path")
        return target

    def put_file(self, key: str, file_path: Path, content_type: str = "application/octet-stream") -> None:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file_path, dest)

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def download_file(self, key: str, dest_path: Path) -> None:
        src = self._resolve(key)
        if not src.exists():
            raise FileNotFoundError(key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest_path)

    def get_bytes(self, key: str) -> bytes:
        src = self._resolve(key)
        if not src.exists():
            raise FileNotFoundError(key)
        return src.read_bytes()

    def get_size(self, key: str) -> int:
        src = self._resolve(key)
        if not src.exists():
            raise FileNotFoundError(key)
        return src.stat().st_size

    def iter_range(
        self, key: str, start: int, end: int, chunk_size: int = 262144
    ) -> Iterator[bytes]:
        src = self._resolve(key)
        if not src.exists():
            raise FileNotFoundError(key)
        remaining = end - start + 1
        with src.open("rb") as fh:
            fh.seek(start)
            while remaining > 0:
                chunk = fh.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).is_file()
        except ValueError:
            return False

    def delete_prefix(self, prefix: str) -> None:
        target = self._resolve(prefix.rstrip("/"))
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.is_file():
            target.unlink(missing_ok=True)

    def healthcheck(self) -> bool:
        return self.root.exists() and self.root.is_dir()

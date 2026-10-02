"""Storage abstraction.

    Application ──► StorageService ──┬─► LocalStorage   (default; files under STORAGE_DIR)
                                     └─► S3Storage      (STORAGE_BACKEND=s3; any S3-compatible service)

Processing steps (PyMuPDF, Pillow, ffmpeg, tesseract) need a real file, so every backend keeps a *working copy*
under STORAGE_DIR; S3Storage additionally mirrors each object to the bucket and can restore a missing working
copy (e.g. after a free-tier restart wiped the disk). Keys are relative, slash-separated and validated, so a key can
never escape STORAGE_DIR.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("polarnexus.storage")

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,400}$")


class StorageError(RuntimeError):
    pass


def _check_key(key: str) -> str:
    if not _KEY_RE.match(key) or ".." in key.split("/") or key.startswith("/"):
        raise StorageError("Invalid storage key.")
    return key


class LocalStorage:
    name = "local"

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.STORAGE_DIR).resolve()

    def path(self, key: str) -> Path:
        p = (self.root / _check_key(key)).resolve()
        if not p.is_relative_to(self.root):
            raise StorageError("Invalid storage key.")
        return p

    def save_bytes(self, key: str, data: bytes) -> str:
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def save_file(self, key: str, src: Path) -> str:
        p = self.path(key)
        if p != Path(src).resolve():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(Path(src).read_bytes())
        return key

    def local_path(self, key: str) -> Path:
        p = self.path(key)
        if not p.exists():
            raise StorageError("Stored file not found.")
        return p

    def exists(self, key: str) -> bool:
        try:
            return self.path(key).exists()
        except StorageError:
            return False

    def delete(self, key: str) -> None:
        try:
            self.path(key).unlink(missing_ok=True)
        except StorageError:
            pass

    def describe(self) -> dict:
        return {"backend": self.name, "location": "local disk (STORAGE_DIR)", "durable": False}


class S3Storage(LocalStorage):
    """S3-compatible object storage (AWS S3, Cloudflare R2, MinIO, Supabase Storage S3 API…). Requires boto3."""

    name = "s3"

    def __init__(self) -> None:
        super().__init__()
        try:
            import boto3  # optional dependency: pip install boto3
        except ImportError as exc:  # pragma: no cover - depends on deployment
            raise StorageError("STORAGE_BACKEND=s3 requires the 'boto3' package.") from exc
        if not settings.S3_BUCKET:
            raise StorageError("STORAGE_BACKEND=s3 requires S3_BUCKET.")
        self.bucket = settings.S3_BUCKET
        self.prefix = settings.S3_PREFIX
        self.client = boto3.client(
            "s3", endpoint_url=settings.S3_ENDPOINT_URL or None, region_name=settings.S3_REGION or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None, aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None)

    def _obj(self, key: str) -> str:
        return f"{self.prefix}{_check_key(key)}"

    def save_bytes(self, key: str, data: bytes) -> str:
        super().save_bytes(key, data)
        self.client.put_object(Bucket=self.bucket, Key=self._obj(key), Body=data)
        return key

    def save_file(self, key: str, src: Path) -> str:
        super().save_file(key, src)
        self.client.upload_file(str(self.path(key)), self.bucket, self._obj(key))
        return key

    def local_path(self, key: str) -> Path:
        p = self.path(key)
        if not p.exists():  # restore the working copy from the bucket
            p.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.bucket, self._obj(key), str(p))
        return p

    def exists(self, key: str) -> bool:
        if super().exists(key):
            return True
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._obj(key))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        super().delete(key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._obj(key))
        except Exception as exc:  # never fail a request because the mirror is unreachable
            log.warning("could not delete %s from object storage: %s", key, exc)

    def describe(self) -> dict:
        return {"backend": self.name, "location": f"s3://{self.bucket}/{self.prefix}", "durable": True,
                "endpoint": settings.S3_ENDPOINT_URL or "AWS default"}


_instance: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _instance
    if _instance is None:
        if settings.STORAGE_BACKEND.lower() == "s3":
            try:
                _instance = S3Storage()
            except StorageError as exc:
                log.error("%s — falling back to local storage", exc)
                _instance = LocalStorage()
        else:
            _instance = LocalStorage()
    return _instance


def key_for_path(path: str | Path) -> str | None:
    """Converts an absolute path inside STORAGE_DIR (as stored by v1/v2 rows) to a storage key."""
    try:
        p = Path(path).resolve()
        root = Path(settings.STORAGE_DIR).resolve()
        return p.relative_to(root).as_posix() if p.is_relative_to(root) else None
    except (OSError, ValueError):
        return None


def mirror(path: str | Path) -> None:
    """Mirrors a file written by an existing (v1/v2) pipeline to object storage when S3 is configured."""
    st = get_storage()
    if st.name == "local":
        return
    key = key_for_path(path)
    if key:
        try:
            st.save_file(key, Path(path))
        except Exception as exc:
            log.warning("object-storage mirror failed for %s: %s", key, exc)

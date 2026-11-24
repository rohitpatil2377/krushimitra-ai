"""Minimal object-storage wrapper.

MVP: store uploaded images on local disk under ./_storage so the backend runs with no AWS account.
Swap `LocalStorage` for an S3 implementation (boto3) by flipping `get_storage()` once AWS is set up.
The rest of the app only depends on the `Storage` interface.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

_STORAGE_DIR = Path("_storage")


class Storage(Protocol):
    def put_image(self, data: bytes, ext: str = "jpg") -> str: ...
    def url_for(self, key: str) -> str: ...


class LocalStorage:
    """Saves bytes to ./_storage and returns the relative key. Good enough for local dev."""

    def __init__(self, base: Path = _STORAGE_DIR) -> None:
        self.base = base
        self.base.mkdir(parents=True, exist_ok=True)

    def put_image(self, data: bytes, ext: str = "jpg") -> str:
        key = f"{uuid.uuid4().hex}.{ext}"
        (self.base / key).write_bytes(data)
        return key

    def url_for(self, key: str) -> str:
        return f"/static/{key}"


def get_storage() -> Storage:
    # TODO: return an S3Storage(boto3) implementation when settings.s3_* are configured.
    return LocalStorage()

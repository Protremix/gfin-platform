# GFIN Object Storage Abstraction Interface
#
# Layer A (current): LocalObjectStorage — local filesystem
# Layer B (target):  S3ObjectStorage — S3-compatible storage (REQUIRES EXTERNAL INFRASTRUCTURE)
#
# Per Master Spec §10: Evidence Vault requires secure object storage with hashing,
# provenance, access policy, audit, and retention. Use WORM-compatible storage
# for evidence classes requiring immutability.

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class StorageObject(BaseModel):
    """Metadata for a stored object."""

    key: str
    content_type: str
    size: int
    content_hash: str
    storage_uri: str
    metadata: dict[str, str] = Field(default_factory=dict)


class ObjectStorage(ABC):
    """Abstract object storage interface.

    All application code stores/retrieves through this interface.
    The specific adapter (local filesystem, S3) is selected by configuration.
    """

    @abstractmethod
    async def store(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> StorageObject:
        """Store an object. Returns storage metadata including content hash."""
        ...

    @abstractmethod
    async def retrieve(self, key: str) -> bytes | None:
        """Retrieve an object by key. Returns None if not found."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete an object. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an object exists."""
        ...

    @abstractmethod
    async def get_metadata(self, key: str) -> StorageObject | None:
        """Get object metadata without downloading content."""
        ...


class LocalObjectStorage(ObjectStorage):
    """Development adapter — local filesystem storage.

    NOT for production. No replication, no WORM, no lifecycle policies.
    Production uses S3-compatible adapter (REQUIRES EXTERNAL INFRASTRUCTURE).

    Suitable for development and testing. Evidence stored here is NOT
    immutable or WORM-compliant.
    """

    def __init__(self, base_path: str = "/tmp/gfin-storage") -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def store(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> StorageObject:
        import hashlib

        file_path = self._base / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

        content_hash = hashlib.sha256(data).hexdigest()

        return StorageObject(
            key=key,
            content_type=content_type,
            size=len(data),
            content_hash=content_hash,
            storage_uri=f"file://{file_path}",
        )

    async def retrieve(self, key: str) -> bytes | None:
        file_path = self._base / key
        if not file_path.exists():
            return None
        return file_path.read_bytes()

    async def delete(self, key: str) -> bool:
        file_path = self._base / key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        return (self._base / key).exists()

    async def get_metadata(self, key: str) -> StorageObject | None:
        import hashlib

        file_path = self._base / key
        if not file_path.exists():
            return None
        data = file_path.read_bytes()
        return StorageObject(
            key=key,
            content_type="application/octet-stream",
            size=len(data),
            content_hash=hashlib.sha256(data).hexdigest(),
            storage_uri=f"file://{file_path}",
        )

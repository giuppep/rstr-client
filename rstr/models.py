"""Data models representing the entities returned by the API client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, repr=False)
class Blob:
    """Class representing a single blob (with metadata).

    Attributes:
        reference (str): the unique reference to the blob (i.e. the ``sha256`` hash of its content).
        content (bytes): the content of the blob in bytes.
        metadata (BlobMetadata): the blob's metadata (filename, mimetype, size...).
    """

    reference: str
    content: bytes
    metadata: "BlobMetadata"

    def __repr__(self) -> str:
        return f"Blob({self.reference[:10]})"


@dataclass(frozen=True, repr=False)
class BlobMetadata:
    """Class representing as single blob's metadata.

    Attributes:
        filename (str): the blob's filename.
        size (int): the size of the blob in bytes.
        mime (str): the mime-type of the blob as a string (e.g. ``image/png``).
        created (datetime): when the blob was first created.
    """

    filename: str
    size: int
    mime: str
    created: datetime

    def __repr__(self) -> str:
        return f"BlobMetadata('{self.filename}', '{self.mime}', {self.size} bytes)"

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from requests.structures import CaseInsensitiveDict


@dataclass
class Blob:
    reference: str
    content: bytes
    metadata: "BlobMetadata"

    def __repr__(self) -> str:
        return f"Blob({self.reference[:10]})"


@dataclass
class BlobMetadata:
    filename: str
    size: int
    mime: str
    created: datetime

    def __repr__(self) -> str:
        return f"BlobMetadata('{self.filename}', '{self.mime}', {self.size} bytes)>"

    @classmethod
    def from_headers(cls, headers: CaseInsensitiveDict) -> "BlobMetadata":
        return cls(
            filename=headers["filename"],
            size=headers["content-length"],
            created=datetime.fromisoformat(headers["created"]),
            mime=headers["content-type"],
        )

from __future__ import annotations

import io
import os
from contextlib import ExitStack
from typing import IO, Any, Optional, Union

from requests import Response, request

from .models import Blob, BlobMetadata

# https://stackoverflow.com/questions/53418046/how-do-i-type-hint-a-filename-in-a-function
File = Union[str, bytes, os.PathLike]
FilePathOrBuffer = Union[File, IO[bytes], io.BufferedReader]

MAX_BATCH_SIZE = 100

VALID_REQUEST_METHODS = ("get", "post", "delete", "put", "head")


class Rustore:
    def __init__(
        self,
        url: Optional[str] = os.getenv("RUSTORE_URL"),
        api_key: Optional[str] = os.getenv("RUSTORE_API_KEY"),
    ) -> None:
        if url is None or api_key is None:
            raise Exception("Must specify URL and API key")

        self.url: str = url
        self.api_key: str = api_key

    def __repr__(self) -> str:
        return f'Rustore("{self.url}")'

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    def _request(self, endpoint: str, method: str = "get", **kwargs: Any) -> Response:
        method = method.lower()
        if method not in VALID_REQUEST_METHODS:
            raise AttributeError(f"'method' must be one of {VALID_REQUEST_METHODS}")

        response = request(
            method, f"{self.url}/{endpoint}", headers=self._headers, **kwargs
        )

        response.raise_for_status()
        return response

    def status_ok(self) -> bool:
        """Check the status of the rustore server

        Returns:
            bool: returns true if the server is running
        """
        return self._request("status").status_code == 200

    def get(self, reference: str) -> Blob:
        """Get a blob from the blob store

        Args:
            reference (str): the reference to the blob

        Returns:
            Blob: the blob retrieved from the blob store
        """
        response = self._request(f"blobs/{reference}")
        metadata = BlobMetadata.from_headers(response.headers)
        return Blob(reference=reference, content=response.content, metadata=metadata)

    def add(
        self,
        files: list[bytes],
        batch_size: int = MAX_BATCH_SIZE,
    ) -> list[str]:
        """Upload a batch of files to the blob store.

        Args:
            files (list[FilePathOrBuffer]): a list of paths or file-like objects to upload
            batch_size (int, optional): How many documents to upload at once. Defaults to MAX_BATCH_SIZE.

        Returns:
           list[str] a list of references to the blobs

        Examples:
            Upload a file given its path

            >>> rustore = Rustore(api_key=API_KEY, url=URL)
            >>> rustore.add(["/path/to/my/file.pdf"])
            ['adb7c6e89f4e7b7cfdaee9b2eae0a7202a83af26cde43d2cf2d25badce05675d']
        """
        batch_size = min(batch_size, MAX_BATCH_SIZE)
        blob_refs: list[str] = []

        # TODO use session
        for batch_number in range(len(files) // batch_size + 1):
            batch_files = files[
                batch_number * batch_size : (batch_number + 1) * batch_size
            ]

            files_to_upload: list[tuple[str, bytes]] = []
            with ExitStack() as stack:
                for file in batch_files:
                    if isinstance(file, (io.BufferedReader, io.BytesIO)):
                        files_to_upload.append(("file", file))
                    elif isinstance(file, str):
                        files_to_upload.append(
                            ("file", stack.enter_context(open(file, "rb")))
                        )
                    else:
                        raise TypeError
                blob_refs.extend(
                    self._request("blobs", "post", files=files_to_upload).json()
                )
        return blob_refs

    def metadata(self, reference: str) -> BlobMetadata:
        """Get a blob's metadata from the blob store.

        Args:
            reference (str): a reference to the blob

        Returns:
            BlobMetadata: the metadata relative to the blob
        """
        response = self._request(f"blobs/{reference}", "head")
        return BlobMetadata.from_headers(response.headers)

    def delete(self, reference: str) -> None:
        """Delete a blob from the blob store

        Args:
            reference (str): the reference to the blob that should be deleted
        """
        self._request(f"blobs/{reference}", "delete")

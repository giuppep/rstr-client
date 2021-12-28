"""Rstr REST API client."""

from __future__ import annotations

import io
import os
from contextlib import ExitStack
from enum import Enum
from typing import IO, Any, Optional, Union
from urllib.parse import urljoin

from requests import PreparedRequest, Response, request
from requests.auth import AuthBase

from .exceptions import (
    BlobNotFound,
    InvalidReference,
    InvalidToken,
    InvalidURL,
    ServerError,
)
from .models import Blob, BlobMetadata

# https://stackoverflow.com/questions/53418046/how-do-i-type-hint-a-filename-in-a-function
File = Union[str, bytes, os.PathLike]
FilePathOrBuffer = Union[File, IO[bytes], io.BufferedReader]

MAX_BATCH_SIZE = 100

VALID_REQUEST_METHODS = ("get", "post", "delete", "put", "head")


class RequestMethods(str, Enum):
    GET = "get"
    HEAD = "head"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class Rstr:
    def __init__(
        self,
        url: Optional[str] = os.getenv("RSTR_URL"),
        token: Optional[str] = os.getenv("RSTR_API_TOKEN"),
    ) -> None:
        """Class for interacting with a remote blob store.

        Args:
            url (Optional[str], optional): The url of the remote blob store.
                Defaults to the value of the environment variable RSTR_URL.
            token (Optional[str], optional): The API token used for authentication.
                Defaults to the value of the environment variable RSTR_API_TOKEN.

        Raises:
            InvalidURL: if no URL is specified.
            InvalidToken: if no token is specified.
        """
        if url is None:
            raise InvalidURL("Must specify a valid URL.")

        if token is None:
            raise InvalidToken("Must specify a valid API token.")

        self.url: str = url
        self._auth = _TokenAuth(token)

    def __repr__(self) -> str:
        return f'Rstr("{self.url}")'

    def _request(
        self, endpoint: str, method: RequestMethods, **kwargs: Any
    ) -> Response:
        response = request(
            method.value, urljoin(self.url, endpoint), auth=self._auth, **kwargs
        )

        if response.status_code == 500:
            raise ServerError
        elif response.status_code == 401:
            raise InvalidToken(
                "Unauthorized: the specified API token does not match any entry."
            )

        return response

    def status_ok(self) -> bool:
        """Check the status of the rstr server.

        Returns:
            bool: returns true if the server is running

        Raises:
            InvalidToken: if the authentication fails.
        """
        return self._request("status", RequestMethods.GET).status_code == 200

    def get(self, reference: str) -> Blob:
        """Get a blob from the blob store.

        Args:
            reference (str): the reference to the blob

        Returns:
            Blob: the blob retrieved from the blob store

        Raises:
            BlobNotFound: if no blob corresponding to the reference is present on the server.
            InvalidReference: if the reference is malformed.
            InvalidToken: if the authentication fails.
        """
        response = self._request(f"blobs/{reference}", RequestMethods.GET)

        if response.status_code == 404:
            raise BlobNotFound(f"The blob {reference} was not found.")
        elif response.status_code == 400:
            raise InvalidReference(f"The reference {reference} is invalid.")
        else:
            response.raise_for_status()

        metadata = BlobMetadata.from_headers(response.headers)
        return Blob(reference=reference, content=response.content, metadata=metadata)

    def add(
        self,
        files: list[FilePathOrBuffer],
        batch_size: int = MAX_BATCH_SIZE,
    ) -> list[str]:
        """Upload a batch of files to the blob store.

        Args:
            files (list[FilePathOrBuffer]): a list of paths or file-like objects to upload
            batch_size (int, optional): How many documents to upload at once. Defaults to MAX_BATCH_SIZE.

        Returns:
           list[str] a list of references to the blobs

        Raises:
            InvalidToken: if the authentication fails.

        Examples:
            Upload a file given its path

            >>> rstr = Rstr(api_key=API_KEY, url=URL)
            >>> rstr.add(["/path/to/my/file.pdf"])
            ['adb7c6e89f4e7b7cfdaee9b2eae0a7202a83af26cde43d2cf2d25badce05675d']
        """
        batch_size = min(batch_size, MAX_BATCH_SIZE)
        blob_refs: list[str] = []

        # TODO use session
        for batch_number in range(len(files) // batch_size + 1):
            batch_files = files[
                batch_number * batch_size : (batch_number + 1) * batch_size
            ]

            files_to_upload: list[tuple[str, Union[bytes, IO[bytes]]]] = []
            with ExitStack() as stack:
                for file in batch_files:
                    if isinstance(file, (io.BufferedReader, io.BytesIO, bytes)):
                        files_to_upload.append(("file", file))
                    elif isinstance(file, str):
                        files_to_upload.append(
                            ("file", stack.enter_context(open(file, "rb")))
                        )
                    else:
                        raise TypeError
                response = self._request(
                    "blobs", RequestMethods.POST, files=files_to_upload
                )
                blob_refs.extend(response.json())
        return blob_refs

    def metadata(self, reference: str) -> BlobMetadata:
        """Get a blob's metadata from the blob store.

        Args:
            reference (str): a reference to the blob

        Returns:
            BlobMetadata: the metadata relative to the blob

        Raises:
            BlobNotFound: if no blob corresponding to the reference is present on the server.
            InvalidReference: if the reference is malformed.
            InvalidToken: if the authentication fails.
        """
        response = self._request(f"blobs/{reference}", RequestMethods.HEAD)

        if response.status_code == 404:
            raise BlobNotFound(f"The blob {reference} was not found.")
        elif response.status_code == 400:
            raise InvalidReference(f"The reference {reference} is invalid.")
        else:
            response.raise_for_status()

        return BlobMetadata.from_headers(response.headers)

    def delete(self, reference: str) -> None:
        """Delete a blob from the blob store.

        Args:
            reference (str): the reference to the blob that should be deleted

        Raises:
            BlobNotFound: if no blob corresponding to the reference is present on the server.
            InvalidReference: if the reference is malformed.
            InvalidToken: if the authentication fails.
        """
        response = self._request(f"blobs/{reference}", RequestMethods.DELETE)

        if response.status_code == 404:
            raise BlobNotFound(f"The blob {reference} was not found.")
        elif response.status_code == 400:
            raise InvalidReference(f"The reference {reference} is invalid.")
        else:
            response.raise_for_status()


class _TokenAuth(AuthBase):
    def __init__(self, token: str) -> None:
        """Class for handling simple token-based authentication used in rstr.

        Args:
            token (str): the API token provided by your rstr instance.
        """
        self.token = token

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        r.headers["X-Auth-Token"] = self.token
        return r

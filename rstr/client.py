"""Rstr REST API client."""

from __future__ import annotations

import io
import os
from contextlib import ExitStack
from datetime import datetime
from enum import Enum
from typing import IO, Any, Optional, Union
from urllib.parse import urljoin

from requests import PreparedRequest, Response, Session
from requests.auth import AuthBase
from requests.structures import CaseInsensitiveDict

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
URL_ENV_VAR = "RSTR_URL"
TOKEN_ENV_VAR = "RSTR_TOKEN"


class _RequestMethods(str, Enum):
    GET = "get"
    HEAD = "head"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class Rstr:
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None) -> None:
        """Class for interacting with a remote blob store.

        It is recommended that this is used as a context manager:

        >>> with Rstr(url=url, token=token) as rstr:
        >>>     blob = rsrt.get(...)

        but it can also be used as a normal object

        >>> rstr = Rstr(url=url, token=token)
        >>> blob = rstr.get(...)

        in which case the HTTP session will be initialized by the constructor and closed
        by the destructor.

        Args:
            url (Optional[str], optional): The url of the remote blob store.
                Defaults to the value of the environment variable ``RSTR_URL``.
            token (Optional[str], optional): The API token used for authentication.
                Defaults to the value of the environment variable ``RSTR_TOKEN``.

        Raises:
            InvalidURL: if no URL is specified.
            InvalidToken: if no token is specified.
        """
        url = url or os.getenv(URL_ENV_VAR)
        if url is None:
            raise InvalidURL("Must specify a valid URL.")

        token = token or os.getenv(TOKEN_ENV_VAR)
        if token is None:
            raise InvalidToken("Must specify a valid API token.")

        self.url: str = url
        self._token = token
        self._session: Optional[Session] = None

    def __repr__(self) -> str:
        return f'Rstr("{self.url}")'

    def _init_session(self) -> None:
        if self._session is None:
            self._session = Session()
            self._session.auth = _TokenAuth(self._token)

    def _close_session(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self) -> "Rstr":
        self._init_session()
        return self

    def __exit__(self, *_: Any) -> None:
        self._close_session()

    def __del__(self) -> None:
        self._close_session()

    @staticmethod
    def _headers_to_metadata(headers: CaseInsensitiveDict) -> BlobMetadata:
        """Build a BlobMetadata object from the `headers` attribute of a `requests.Response` object.

        The blob's metadata is specified in the HTTP response headers.

        Returns:
            BlobMetadata: the blob's metadata
        """
        return BlobMetadata(
            filename=headers["filename"],
            size=int(headers["content-length"]),
            created=datetime.fromisoformat(headers["created"]),
            mime=headers["content-type"],
        )

    def _request(
        self, endpoint: str, method: _RequestMethods, **kwargs: Any
    ) -> Response:
        if self._session is None:
            self._init_session()

        assert self._session is not None

        response = self._session.request(
            method.value, urljoin(self.url, endpoint), **kwargs
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

        Example:
            >>> with Rstr(url=url, token=token) as rstr:
            >>>     assert rstr.status_ok()
        """
        return self._request("status", _RequestMethods.GET).status_code == 200

    def add(
        self,
        files: list[FilePathOrBuffer],
        batch_size: int = MAX_BATCH_SIZE,
    ) -> list[str]:
        """Upload a batch of files to the blob store.

        Args:
            files (list[FilePathOrBuffer]): a list of paths or file-like objects to upload
            batch_size (int, optional): How many documents to upload at once.
                Defaults to ``MAX_BATCH_SIZE``.

        Returns:
           list[str] a list of references to the blobs

        Raises:
            InvalidToken: if the authentication fails.

        Example:
            Upload a file given its path

            >>> with Rstr(url=url, token=token) as rstr:
            >>>     refs = rstr.add(["/path/to/my/file.pdf"])
            >>> print(refs)
            ['eb8471d882d2a90a4b1c60dcaa41fc5d0c33143f8ebc910247453a130e74ca68']
        """
        batch_size = min(batch_size, MAX_BATCH_SIZE)
        blob_refs: list[str] = []

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
                    "blobs", _RequestMethods.POST, files=files_to_upload
                )
                blob_refs.extend(response.json())
        return blob_refs

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

        Example:
            Download a file given its reference

            >>> ref = "eb8471d882..."
            >>> with Rstr(url=url, token=token) as rstr:
            >>>     blob = rstr.get(ref)
            >>> print(blob)
            Blob(eb8471d882)
            >>> blob.content
            b"..."
            >>> blob.metadata
            BlobMetadata('file.pdf', 'application/pdf', 1024 bytes)
        """
        response = self._request(f"blobs/{reference}", _RequestMethods.GET)

        if response.status_code == 404:
            raise BlobNotFound(f"The blob {reference} was not found.")
        elif response.status_code == 400:
            raise InvalidReference(f"The reference {reference} is invalid.")
        else:
            response.raise_for_status()

        metadata = self._headers_to_metadata(response.headers)
        return Blob(reference=reference, content=response.content, metadata=metadata)

    def metadata(self, reference: str) -> BlobMetadata:
        """Get a blob's metadata from the blob store without downloading the blob's content.

        Args:
            reference (str): a reference to the blob

        Returns:
            BlobMetadata: the metadata relative to the blob

        Raises:
            BlobNotFound: if no blob corresponding to the reference is present on the server.
            InvalidReference: if the reference is malformed.
            InvalidToken: if the authentication fails.

        Example:
            >>> ref = "eb8471d882..."
            >>> with Rstr(url=url, token=token) as rstr:
            >>>     blob_metadata = rstr.metadata(ref)
            >>> blob_metadata
            BlobMetadata('file.pdf', 'application/pdf', 1024 bytes)
        """
        response = self._request(f"blobs/{reference}", _RequestMethods.HEAD)

        if response.status_code == 404:
            raise BlobNotFound(f"The blob {reference} was not found.")
        elif response.status_code == 400:
            raise InvalidReference(f"The reference {reference} is invalid.")
        else:
            response.raise_for_status()

        return self._headers_to_metadata(response.headers)

    def delete(self, reference: str) -> None:
        """Permanently delete a blob from the blob store.

        Args:
            reference (str): the reference to the blob that should be deleted

        Raises:
            BlobNotFound: if no blob corresponding to the reference is present on the server.
            InvalidReference: if the reference is malformed.
            InvalidToken: if the authentication fails.

        Example:
            >>> ref = "eb8471d882..."
            >>> with Rstr(url=url, token=token) as rstr:
            >>>     rstr.delete(ref)
            >>>     blob = rstr.get(ref)
            rstr.exceptions.BlobNotFound: The blob eb8471d882... was not found.
        """
        response = self._request(f"blobs/{reference}", _RequestMethods.DELETE)

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

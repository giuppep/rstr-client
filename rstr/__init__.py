"""Python client for the `Rstr <https://github.com/giuppep/rstr>`_ blob store.

Basic usage
***********

Upload a file to the blob store:


   >>> from rstr import Rstr
   >>> url = "https://my-rstr.rs"
   >>> token = "*****"
   >>> with Rstr(url=url, token=token) as rstr:
   >>>     refs = rstr.add(["/path/to/my/file.pdf"])
   >>> print(refs)
   ["eb8471d882d2a90a4b1c60dcaa41fc5d0c33143f8ebc910247453a130e74ca68"]

Retrieve a file from the blob store:

   >>> with Rstr(url=url, token=token) as rstr:
   >>>     blob = rstr.get(refs[0])
   >>> print(blob)
   Blob(eb8471d882)
   >>> blob.content
   b"..."

"""
from .client import Rstr
from .exceptions import (
    BlobNotFound,
    InvalidReference,
    InvalidToken,
    InvalidURL,
    RstrException,
    ServerError,
)
from .models import Blob, BlobMetadata

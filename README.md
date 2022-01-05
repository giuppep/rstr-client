# rstr-client

A lightweight `python` API client for the [`rstr`](https://github.com/giuppep/rstr) blob store.

## Installation

You can install the `rstr-client` library with `pip`

```
pip install rstr-client
```

## Usage

```python
from rstr import Rstr

# Initialise the rstr client with the URL to your rstr server
# and your API Token.
# NOTE: these can be specified as environment variables
# >>> export RSTR_URL="https://my-rstr.rs"
# >>> export RSTR_TOKEN="MY_API_TOKEN"
url = "https://my-rstr.rs"
token = "MY_API_TOKEN"

with Rstr(url=url, token=token) as rstr:
    # Add a file to the blob store
    refs = rstr.add(["/path/to/my/file.txt"])

    # You will get a list of references to your blobs
    # e.g. ["f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de"]

    # You can then use the reference to retrieve your blob
    ref = refs[0]
    blob = rstr.get(ref)

print(blob)
# Blob(f29bc64a9d)

print(blob.metadata)
# BlobMetadata('file.txt', 'text/plain', 20 bytes)

# You can access the binary content of the blob with:
# content = blob.content

# The blob can be permanently deleted from the blob store with:
with Rstr(url=url, token=token) as rstr:
    rstr.delete(ref)
```

## License

Copyright (c) 2021 giuppep

`rstr-client` is made available under the [MIT License](LICENSE)
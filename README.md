# rstr-client

A lightweight `python` API client for the [`rstr`](https://github.com/giuppep/rstr) blob store.

## Installation

TODO

## Usage

```python
from rstr import Rstr

# Initialise the rstr client with the URL to your rstr server
# and your API Tokent.
url = "https://my-rstr.rs"
token = "MY_API_TOKEN"
rstr = Rstr(url, token)

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

# The blob can be permanently deleted from the blob store with
rstr.delete(ref)
```

## License

Copyright (c) 2021 giuppep

`rstr-client` is made available under the [MIT License](LICENSE)
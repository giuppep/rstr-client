# rustore-client

A lightweight `python` API client for the `rustore` blob store.

## Installation

TODO

## Usage

```python
from rustore import Rustore

# Initialise the rustore client with the URL to your rustore server
# and your API Tokent.
url = "https://my-rustore.rs"
token = "MY_API_TOKEN"
rustore = Rustore(url, token)

# Add a file to the blob store
refs = rustore.add(["/path/to/my/file.txt"])

# You will get a list of references to your blobs
# e.g. ["f29bc64a9d3732b4b9035125fdb3285f5b6455778edca72414671e0ca3b2e0de"]

# You can then use the reference to retrieve your blob
ref = refs[0]
blob = rustore.get(ref)

print(blob)
# Blob(f29bc64a9d)

print(blob.metadata)
# BlobMetadata('file.txt', 'text/plain', 20 bytes)

# The blob can be permanently deleted from the blob store with
rustore.delete(ref)
```

## License

Copyright (c) 2021 giuppep

`rustore-client` is made available under the [MIT License](LICENSE)
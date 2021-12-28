class RstrException(Exception):
    """Generic blob store exception."""

    pass


class BlobNotFound(RstrException):
    """The requested blob was not found."""

    pass


class InvalidReference(RstrException):
    """The reference used is invalid."""

    pass


class InvalidURL(RstrException):
    """The specified blob store url is invalid."""

    pass


class InvalidToken(RstrException):
    """The specified blob store token is invalid."""

    pass


class ServerError(RstrException):
    """Unspecified error happened on the server side."""

    pass

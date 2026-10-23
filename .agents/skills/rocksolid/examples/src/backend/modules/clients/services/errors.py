"""The errors the clients module raises to its callers."""


class ClientNotFoundError(Exception):
    """The owner has no client with this ID."""


class InvalidPageError(Exception):
    """The page token is not one this service issued."""


class MailNotConfiguredError(Exception):
    """The module's settings lack what sending email needs, so no retry can send it."""

"""The errors the users module raises to its callers."""


class SignInFailedError(Exception):
    """The caller sent sign-in credentials that are malformed or not valid."""

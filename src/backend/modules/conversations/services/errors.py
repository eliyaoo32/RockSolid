"""The errors the conversations module raises to its callers."""


class ConversationBusyError(Exception):
    """The agent is still answering the conversation's previous message."""


class ConversationNotFoundError(Exception):
    """The caller has no conversation with this agent and thread."""


class InvalidPageError(Exception):
    """The page token is not one this service issued."""

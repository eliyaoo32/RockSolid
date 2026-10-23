"""The errors the conversations module raises to its callers."""


class ConversationBusyError(Exception):
    """The agent is still answering the conversation's previous message."""

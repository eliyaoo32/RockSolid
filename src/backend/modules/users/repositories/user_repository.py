from typing import Protocol

from modules.users.domain.user import User


class UserRepository(Protocol):
    """Finds who signed in."""

    async def from_token(self, token: str) -> User | None:
        """Returns the user a sign-in token belongs to, or None when the token is not valid."""
        ...

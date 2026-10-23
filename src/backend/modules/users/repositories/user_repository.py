from typing import Protocol

from modules.users.domain.user import User


class SignInProvider(Protocol):
    """Finds who signed in, as the provider that issued their sign-in token knows them."""

    async def from_token(self, token: str) -> User | None:
        """Returns the user a sign-in token belongs to, or None when the token is not valid."""
        ...


class UserRepository(Protocol):
    """Keeps what users change about themselves."""

    async def with_saved_changes(self, user: User) -> User:
        """Returns the user with the changes they saved, such as their display name."""
        ...

    async def save(self, user: User) -> None:
        """Saves what users can change about themselves."""
        ...

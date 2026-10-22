"""The users use cases: what signed-in users see and change about themselves."""

from modules.users.domain.user import User
from modules.users.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def current(self, signed_in: User) -> User:
        """The signed-in user, with the changes they saved winning over their sign-in's."""
        return await self._repository.with_saved_changes(signed_in)

    async def change_display_name(self, signed_in: User, display_name: str) -> User:
        """Raises ValidationError when the display name breaks the user's rules."""
        user = signed_in.model_copy()
        user.display_name = display_name
        await self._repository.save(user)
        return user

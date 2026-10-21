"""What every run of an agent gets."""

from dataclasses import dataclass

from pydantic_ai import ModelRetry

from modules.users.domain.user import UserId


@dataclass(frozen=True)
class AgentDeps:
    """Who is calling, or None for an anonymous caller."""

    user_id: UserId | None

    def signed_in_user_id(self) -> UserId:
        """The caller's user ID, for a tool that acts as the user. In an anonymous run, tells
        the model that the user must sign in first."""
        if self.user_id is None:
            raise ModelRetry("The user is not signed in. Ask them to sign in first.")
        return self.user_id

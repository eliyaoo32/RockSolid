from modules.users.domain.user import User
from modules.users.repositories.debug_users import DebugUserRepository

DANA = User(id="debug-user", email="debug-user@example.com", display_name="Dana Levi")


async def test_signs_in_the_debug_user_with_the_debug_token() -> None:
    users = DebugUserRepository("debug-token", "Dana Levi")

    assert await users.from_token("debug-token") == DANA


async def test_signs_in_nobody_with_any_other_token() -> None:
    users = DebugUserRepository("debug-token", "Dana Levi")

    assert await users.from_token("debug-token-2") is None
    assert await users.from_token("") is None
    assert await users.from_token("débug-token") is None

from connectrpc.code import Code

from executables.users_api.tests.framework.driver import UsersDriver
from users.v1.users_pb import User

DANA = User(name="users/uid-dana", display_name="uid-dana", email="uid-dana@example.com")
NOA = User(name="users/uid-noa", display_name="uid-noa", email="uid-noa@example.com")


def named(user: User, display_name: str) -> User:
    return User(name=user.name, display_name=display_name, email=user.email)


async def test_tells_each_signed_in_caller_who_they_are(driver: UsersDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    assert await driver.get.current_user() == DANA

    driver.when.sign_in_as("uid-noa")
    assert await driver.get.current_user() == NOA


async def test_requires_a_valid_sign_in(driver: UsersDriver) -> None:
    for sign_in in [driver.when.sign_out, driver.when.sign_in_with_a_bad_token]:
        sign_in()
        assert await driver.get.current_user() is None
        assert driver.get.error() == Code.UNAUTHENTICATED
        await driver.when.change_display_name("Dana Levi", of=DANA.name)
        assert driver.get.error() == Code.UNAUTHENTICATED

    driver.when.sign_in_as("uid-dana")
    assert await driver.get.current_user() == DANA


async def test_a_user_changes_their_display_name_and_keeps_it(driver: UsersDriver) -> None:
    driver.when.sign_in_as("uid-dana")

    await driver.when.change_display_name("Dana Levi")
    assert driver.get.changed_user() == named(DANA, "Dana Levi")
    # The saved name wins over the one the sign-in gives.
    assert await driver.get.current_user() == named(DANA, "Dana Levi")

    await driver.when.change_display_name("Dana")
    assert await driver.get.current_user() == named(DANA, "Dana")


async def test_refuses_an_invalid_change_and_keeps_the_display_name(driver: UsersDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.change_display_name("Dana Levi")

    for display_name, paths in [
        ("x" * 101, ["display_name"]),
        ("", ["display_name"]),
        ("   ", ["display_name"]),
        ("Dana", ["email"]),
        ("Dana", []),
    ]:
        await driver.when.change_display_name(display_name, paths=paths)
        assert driver.get.error() == Code.INVALID_ARGUMENT, (display_name, paths)
    assert await driver.get.current_user() == named(DANA, "Dana Levi")

    await driver.when.change_display_name("  Dana  ")
    assert await driver.get.current_user() == named(DANA, "Dana")


async def test_each_user_changes_only_themselves(driver: UsersDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    for someone_else in [NOA.name, "users/uid-nobody"]:
        await driver.when.change_display_name("Avi", of=someone_else)
        assert driver.get.error() == Code.PERMISSION_DENIED

    driver.when.sign_in_as("uid-noa")
    assert await driver.get.current_user() == NOA

    # The same display name belongs to each user on their own.
    await driver.when.change_display_name("Avi")
    driver.when.sign_in_as("uid-dana")
    await driver.when.change_display_name("Avi")
    assert await driver.get.current_user() == named(DANA, "Avi")
    driver.when.sign_in_as("uid-noa")
    assert await driver.get.current_user() == named(NOA, "Avi")


async def test_signs_in_only_the_debug_user_on_a_debug_backend(debug_driver: UsersDriver) -> None:
    debug_driver.when.sign_in_as("uid-noa")
    assert await debug_driver.get.current_user() is None
    assert debug_driver.get.error() == Code.UNAUTHENTICATED

    debug_driver.when.sign_in_as("debug")
    debug_user = User(
        name="users/debug-user", display_name="Dana Levi", email="debug-user@example.com"
    )
    assert await debug_driver.get.current_user() == debug_user

    await debug_driver.when.change_display_name("Dana", of=debug_user.name)
    assert await debug_driver.get.current_user() == named(debug_user, "Dana")

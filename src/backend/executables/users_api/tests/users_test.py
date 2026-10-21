from connectrpc.code import Code

from executables.users_api.tests.framework.driver import UsersDriver
from users.v1.users_pb import User

DANA = User(name="users/uid-dana", display_name="uid-dana", email="uid-dana@example.com")
NOA = User(name="users/uid-noa", display_name="uid-noa", email="uid-noa@example.com")


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

    driver.when.sign_in_as("uid-dana")
    assert await driver.get.current_user() == DANA


async def test_signs_in_only_the_debug_user_on_a_debug_backend(debug_driver: UsersDriver) -> None:
    debug_driver.when.sign_in_as("uid-noa")
    assert await debug_driver.get.current_user() is None
    assert debug_driver.get.error() == Code.UNAUTHENTICATED

    debug_driver.when.sign_in_as("debug")
    assert await debug_driver.get.current_user() == User(
        name="users/debug-user", display_name="Dana Levi", email="debug-user@example.com"
    )

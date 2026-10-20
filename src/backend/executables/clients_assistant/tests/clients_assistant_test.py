from executables.clients_assistant.tests.framework.driver import AssistantDriver
from libs.testing.models import FakeModels


async def test_looks_up_and_adds_the_users_clients_in_a_conversation(
    driver: AssistantDriver, models: FakeModels
) -> None:
    added = await driver.when.user_says("uid-dana", "add Avi Cohen | avi@example.com")
    assert added.tool_calls == ["create_client"]
    assert await driver.get.clients_of("uid-dana") == ["Avi Cohen"]

    await driver.when.user_says("uid-dana", "add Noa Bar")
    listed = await driver.when.user_says("uid-dana", "list contains(display_name, 'Noa')")

    assert listed.tool_calls == ["list_clients"]
    assert "Noa Bar" in driver.get.answer()
    assert "Avi Cohen" not in driver.get.answer(), "the filter reached the clients module"
    assert models.asked_for == ["deepseek-v4.1-flash:cloud"]


async def test_acts_only_as_the_signed_in_user(driver: AssistantDriver) -> None:
    await driver.when.user_says("uid-dana", "add Avi Cohen | avi@example.com")
    await driver.when.user_says("uid-moshe", "add Avi Cohen | avi@example.com")
    await driver.when.user_says("uid-moshe", "add Dana Levi")

    await driver.when.user_says("uid-dana", "list ")
    assert "Avi Cohen" in driver.get.answer()
    assert "Dana Levi" not in driver.get.answer(), "Dana never sees Moshe's clients"
    assert await driver.get.clients_of("uid-dana") == ["Avi Cohen"]
    assert set(await driver.get.clients_of("uid-moshe")) == {"Avi Cohen", "Dana Levi"}


async def test_tells_the_model_what_was_invalid_so_it_can_fix_it(driver: AssistantDriver) -> None:
    await driver.when.user_says("uid-dana", "list display_name eq")
    assert "Could not:" in driver.get.answer()
    assert "display_name" in driver.get.answer(), "the complaint lists the filterable fields"

    await driver.when.user_says("uid-dana", "add Avi Cohen | not-an-email")
    assert "Could not: The client is not valid" in driver.get.answer()
    assert await driver.get.clients_of("uid-dana") == []

    await driver.when.user_says("uid-dana", "add Avi Cohen | avi@example.com")
    assert await driver.get.clients_of("uid-dana") == ["Avi Cohen"]


async def test_talks_only_to_signed_in_users(driver: AssistantDriver) -> None:
    refused = await driver.when.user_says(None, "add Avi Cohen")

    assert refused.status == 401
    assert refused.refusal is not None and refused.refusal["code"] == "sign_in_required"
    assert await driver.get.clients_of("uid-dana") == []

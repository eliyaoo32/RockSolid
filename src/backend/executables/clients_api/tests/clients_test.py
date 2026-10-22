from datetime import timedelta

from connectrpc.code import Code

from executables.clients_api.tests.framework.driver import ClientsDriver
from executables.clients_api.tests.framework.fixtures import START


async def test_manages_a_client_from_creation_to_deletion(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")

    await driver.when.create_client("  Avi Cohen  ", email="avi@example.com")
    created = driver.get.last_client()
    assert created.name.startswith("clients/")
    assert created.display_name == "Avi Cohen"
    assert created.email == "avi@example.com"
    assert created.create_time is not None
    assert created.create_time.to_datetime() == START
    assert created.update_time == created.create_time

    fetched = await driver.get.client(created.name)
    assert fetched == created
    assert await driver.get.client_names() == ["Avi Cohen"]

    driver.when.time_passes(timedelta(hours=1))
    await driver.when.update_client(created.name, ["display_name"], display_name="Avi Levi")
    renamed = driver.get.last_client()
    assert renamed.display_name == "Avi Levi"
    assert renamed.email == "avi@example.com"
    assert renamed.create_time == created.create_time
    assert renamed.update_time is not None
    assert renamed.update_time.to_datetime() == START + timedelta(hours=1)

    await driver.when.update_client(created.name, ["email"])
    assert not driver.get.last_client().has_field("email")
    fetched_after_clear = await driver.get.client(created.name)
    assert fetched_after_clear is not None
    assert not fetched_after_clear.has_field("email")

    await driver.when.delete_client(created.name)
    assert driver.get.error() is None
    assert await driver.get.client(created.name) is None
    assert driver.get.error() == Code.NOT_FOUND
    assert await driver.get.client_names() == []


async def test_rejects_invalid_input_and_changes_nothing(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")

    await driver.when.create_client("   ")
    assert driver.get.error() == Code.INVALID_ARGUMENT
    await driver.when.create_client("Avi Cohen", email="not-an-email")
    assert driver.get.error() == Code.INVALID_ARGUMENT
    assert driver.get.error_message() == "client.email: must be a valid email address"
    await driver.when.create_client("A" * 201)
    assert driver.get.error_message() == "client.display_name: must be at most 200 characters"
    await driver.when.create_client("")
    assert driver.get.error_message() == "client.display_name is required"
    assert await driver.get.client_names() == []

    await driver.when.create_client("Avi Cohen")
    name = driver.get.last_client().name
    await driver.when.update_client(name, ["display_name"], display_name="")
    assert driver.get.error() == Code.INVALID_ARGUMENT
    for mask in [[], ["create_time"]]:
        await driver.when.update_client(name, mask)
        assert driver.get.error() == Code.INVALID_ARGUMENT
        assert driver.get.error_message() == (
            "update_mask must name one or more of: display_name, email"
        )
    assert await driver.get.client_names() == ["Avi Cohen"]

    for outside_clients in ["Avi Cohen", "contacts/0f8fad5b-d9cb-469f-a165-70867728950e"]:
        assert await driver.get.client(outside_clients) is None
        assert driver.get.error() == Code.INVALID_ARGUMENT
        assert driver.get.error_message() == "name: does not have prefix `clients/`"
        await driver.when.update_client(outside_clients, ["email"], email="avi@example.com")
        assert driver.get.error_message() == "client.name must start with clients/"
    # The ID after the prefix is opaque, so one we never issued names no client.
    assert await driver.get.client("clients/not-a-uuid") is None
    assert driver.get.error() == Code.NOT_FOUND
    await driver.when.delete_client("clients/not-a-uuid")
    assert driver.get.error() == Code.NOT_FOUND
    assert await driver.get.client_names() == ["Avi Cohen"]


async def test_requires_a_valid_sign_in(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.create_client("Avi Cohen")
    name = driver.get.last_client().name

    for sign_in in [driver.when.sign_out, driver.when.sign_in_with_a_bad_token]:
        sign_in()
        await driver.when.create_client("Noa Bar")
        assert driver.get.error() == Code.UNAUTHENTICATED
        assert await driver.get.client(name) is None
        assert driver.get.error() == Code.UNAUTHENTICATED
        assert await driver.get.client_names() is None
        assert driver.get.error() == Code.UNAUTHENTICATED
        await driver.when.update_client(name, ["display_name"], display_name="Avi Levi")
        assert driver.get.error() == Code.UNAUTHENTICATED
        await driver.when.delete_client(name)
        assert driver.get.error() == Code.UNAUTHENTICATED

    driver.when.sign_in_as("uid-dana")
    assert await driver.get.client_names() == ["Avi Cohen"]


async def test_keeps_each_users_clients_apart(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.create_client("Avi Cohen", email="avi@example.com")
    danas = driver.get.last_client().name
    driver.when.sign_in_as("uid-moshe")
    await driver.when.create_client("Avi Cohen", email="avi@example.com")
    moshes = driver.get.last_client().name

    assert await driver.get.client_names() == ["Avi Cohen"]
    assert await driver.get.client(danas) is None
    assert driver.get.error() == Code.NOT_FOUND
    await driver.when.update_client(danas, ["display_name"], display_name="Taken over")
    assert driver.get.error() == Code.NOT_FOUND
    await driver.when.delete_client(danas)
    assert driver.get.error() == Code.NOT_FOUND
    await driver.when.update_client(moshes, ["display_name"], display_name="Avi Levi")

    driver.when.sign_in_as("uid-dana")
    dana_client = await driver.get.client(danas)
    assert dana_client is not None
    assert dana_client.display_name == "Avi Cohen"
    assert dana_client.email == "avi@example.com"


async def test_lists_clients_newest_first_one_page_at_a_time(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    for display_name in ["Avi Cohen", "Noa Bar", "Dana Levi"]:
        await driver.when.create_client(display_name)
        driver.when.time_passes(timedelta(minutes=1))

    assert await driver.get.client_names(page_size=2) == ["Dana Levi", "Noa Bar"]
    second_page = driver.get.next_page_token()
    assert second_page != ""
    assert await driver.get.client_names(page_size=2, page_token=second_page) == ["Avi Cohen"]
    assert driver.get.next_page_token() == ""

    assert await driver.get.client_names(page_size=1000) == ["Dana Levi", "Noa Bar", "Avi Cohen"]
    assert await driver.get.client_names(page_size=-1) is None
    assert driver.get.error() == Code.INVALID_ARGUMENT
    assert await driver.get.client_names(page_token="not-a-token") is None
    assert driver.get.error() == Code.INVALID_ARGUMENT


async def test_filters_clients(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.create_client("Avi Cohen", email="avi@example.com")
    driver.when.time_passes(timedelta(days=1))
    await driver.when.create_client("Noa Bar")
    driver.when.time_passes(timedelta(days=1))
    await driver.when.create_client("Avi Levi", email="levi@example.com")
    driver.when.sign_in_as("uid-moshe")
    await driver.when.create_client("Avi Cohen")
    driver.when.sign_in_as("uid-dana")

    assert await driver.get.client_names(filter="display_name eq 'Avi Cohen'") == ["Avi Cohen"]
    assert await driver.get.client_names(filter="startswith(display_name, 'Avi')") == [
        "Avi Levi",
        "Avi Cohen",
    ]
    assert await driver.get.client_names(filter="email eq null") == ["Noa Bar"]
    one_day_in = (START + timedelta(hours=12)).isoformat().replace("+00:00", "Z")
    assert await driver.get.client_names(filter=f"create_time gt {one_day_in}") == [
        "Avi Levi",
        "Noa Bar",
    ]

    names = await driver.get.client_names(page_size=1, filter="contains(display_name, 'Avi')")
    assert names == ["Avi Levi"]
    next_page = driver.get.next_page_token()
    filtered = "contains(display_name, 'Avi')"
    assert await driver.get.client_names(page_token=next_page, filter=filtered) == ["Avi Cohen"]
    assert driver.get.next_page_token() == ""


async def test_rejects_an_invalid_filter_and_says_why(driver: ClientsDriver) -> None:
    driver.when.sign_in_as("uid-dana")

    for filter, problem in [
        ("display_name eq", "not a valid filter"),
        ("owner_id eq 'uid-moshe'", "unknown field 'owner_id'"),
        ("create_time gt 'yesterday'", "'create_time' holds date-times"),
    ]:
        assert await driver.get.client_names(filter=filter) is None
        assert driver.get.error() == Code.INVALID_ARGUMENT
        assert problem in driver.get.error_message()
        assert "display_name" in driver.get.error_message()

from datetime import UTC, datetime, timedelta

from connectrpc.code import Code
from protobuf.wkt import Timestamp

from conversations.v1.conversations_pb import Conversation, MessageRole
from executables.conversations_api.tests.framework.driver import ConversationsDriver, name_of
from libs.testing.runtime import START

CLIENTS = "00000000-0000-4000-8000-0000000000a1"
EMAIL = "00000000-0000-4000-8000-0000000000a2"
PLAN = "00000000-0000-4000-8000-0000000000a3"
MOSHES = "00000000-0000-4000-8000-0000000000b1"
# "Plan " * 30, cut to the longest title.
PLAN_TITLE = " ".join(["Plan"] * 20) + "…"


def minutes_after_start(minutes: int) -> Timestamp:
    return Timestamp.from_datetime(START + timedelta(minutes=minutes))


async def test_lists_renames_and_pins_the_users_conversations(driver: ConversationsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.say(CLIENTS, "Who are my clients?")
    driver.when.wait(minutes=1)
    await driver.when.say(EMAIL, "  Draft an email\n to Avi  ")
    driver.when.wait(minutes=1)
    await driver.when.say(PLAN, "Plan " * 30)

    assert await driver.get.conversations() == [
        Conversation(
            name=name_of(PLAN),
            title=PLAN_TITLE,
            last_message_time=minutes_after_start(2),
        ),
        Conversation(
            name=name_of(EMAIL),
            title="Draft an email to Avi",
            last_message_time=minutes_after_start(1),
        ),
        Conversation(
            name=name_of(CLIENTS),
            title="Who are my clients?",
            last_message_time=minutes_after_start(0),
        ),
    ]
    assert driver.get.next_page_token() == ""

    await driver.when.rename(name_of(EMAIL), "  Avi's email  ")
    assert driver.get.changed() == Conversation(
        name=name_of(EMAIL), title="Avi's email", last_message_time=minutes_after_start(1)
    )
    await driver.when.pin(name_of(CLIENTS))
    assert await driver.get.titles() == [
        "pinned: Who are my clients?",
        PLAN_TITLE,
        "Avi's email",
    ]

    # A new message moves the conversation up among the unpinned ones, and keeps its new title.
    driver.when.wait(minutes=1)
    await driver.when.say(EMAIL, "Make it shorter")
    assert await driver.get.titles() == [
        "pinned: Who are my clients?",
        "Avi's email",
        PLAN_TITLE,
    ]

    # Pinned conversations list by their last message too.
    await driver.when.update(
        name_of(PLAN), title="The plan", pinned=True, paths=["title", "pinned"]
    )
    assert await driver.get.titles() == [
        "pinned: The plan",
        "pinned: Who are my clients?",
        "Avi's email",
    ]

    await driver.when.pin(name_of(CLIENTS), pinned=False)
    await driver.when.pin(name_of(PLAN), pinned=False)
    assert await driver.get.titles() == ["Avi's email", "The plan", "Who are my clients?"]


async def test_opens_a_conversation_with_its_text_messages(driver: ConversationsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    sent_after = datetime.now(UTC)
    await driver.when.say(EMAIL, "Draft an email to Avi")
    driver.when.wait(minutes=5)
    await driver.when.say(EMAIL, "Make it shorter")
    sent_before = datetime.now(UTC)

    opened = await driver.get.conversation(name_of(EMAIL))

    assert opened is not None
    conversation, messages = opened
    assert conversation == Conversation(
        name=name_of(EMAIL), title="Draft an email to Avi", last_message_time=minutes_after_start(5)
    )
    assert [(m.role, m.text) for m in messages] == [
        (MessageRole.USER, "Draft an email to Avi"),
        (MessageRole.ASSISTANT, "You said: Draft an email to Avi"),
        (MessageRole.USER, "Make it shorter"),
        (MessageRole.ASSISTANT, "You said: Make it shorter"),
    ]
    times = [m.send_time.to_datetime() for m in messages if m.send_time is not None]
    assert len(times) == 4
    assert times == sorted(times)
    assert sent_after <= times[0] and times[-1] <= sent_before, "each was sent during the test"


async def test_pages_through_the_conversations_pinned_ones_first(
    driver: ConversationsDriver,
) -> None:
    driver.when.sign_in_as("uid-dana")
    for thread, text in [(CLIENTS, "clients"), (EMAIL, "email"), (PLAN, "plan")]:
        await driver.when.say(thread, text)
        driver.when.wait(minutes=1)
    await driver.when.pin(name_of(CLIENTS))

    pages: list[list[str]] = []
    token = ""
    while True:
        page = await driver.get.conversations(page_size=1, page_token=token)
        assert page is not None, driver.get.error()
        pages.append([c.title for c in page])
        token = driver.get.next_page_token()
        if not token:
            break

    assert pages == [["clients"], ["plan"], ["email"]]
    first_two = await driver.get.conversations(page_size=2)
    assert [c.title for c in first_two or []] == ["clients", "plan"]

    for forged in ["not-a-token", "WyJ4Il0=", "e30="]:
        assert await driver.get.conversations(page_token=forged) is None
        assert driver.get.error() == Code.INVALID_ARGUMENT, forged
    assert await driver.get.titles() == ["pinned: clients", "plan", "email"]


async def test_lists_each_agents_conversations_apart(driver: ConversationsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.say(CLIENTS, "Who are my clients?")
    await driver.when.say(CLIENTS, "What can you do?", to="helper")

    assert await driver.get.titles() == ["Who are my clients?"]
    assert await driver.get.titles("agents/helper") == ["What can you do?"]
    assert await driver.get.titles("agents/never_talked_to") == []
    assert await driver.get.conversation(name_of(CLIENTS, agent="helper")) is not None


async def test_requires_a_valid_sign_in_and_changes_nothing(driver: ConversationsDriver) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.say(CLIENTS, "Who are my clients?")

    for sign_in in [driver.when.sign_out, driver.when.sign_in_with_a_bad_token]:
        sign_in()
        assert await driver.get.conversations() is None
        assert driver.get.error() == Code.UNAUTHENTICATED
        assert await driver.get.conversation(name_of(CLIENTS)) is None
        assert driver.get.error() == Code.UNAUTHENTICATED
        await driver.when.update(
            name_of(CLIENTS), title="Taken", pinned=True, paths=["title", "pinned"]
        )
        assert driver.get.error() == Code.UNAUTHENTICATED

    driver.when.sign_in_as("uid-dana")
    assert await driver.get.titles() == ["Who are my clients?"]


async def test_each_user_reaches_only_their_own_conversations(driver: ConversationsDriver) -> None:
    # Dana and Moshe hold identical conversations: the same thread, the same message.
    for user in ["uid-dana", "uid-moshe"]:
        driver.when.sign_in_as(user)
        await driver.when.say(CLIENTS, "Who are my clients?")
    driver.when.wait(minutes=1)
    await driver.when.say(MOSHES, "Moshe's own")

    driver.when.sign_in_as("uid-dana")
    assert await driver.get.titles() == ["Who are my clients?"]
    for request in ["get", "rename", "pin"]:
        if request == "get":
            assert await driver.get.conversation(name_of(MOSHES)) is None
        elif request == "rename":
            await driver.when.rename(name_of(MOSHES), "Taken")
        else:
            await driver.when.pin(name_of(MOSHES))
        assert driver.get.error() == Code.NOT_FOUND, request

    # The same thread belongs to each user on their own.
    await driver.when.rename(name_of(CLIENTS), "Dana's clients")
    await driver.when.pin(name_of(CLIENTS))
    assert await driver.get.titles() == ["pinned: Dana's clients"]

    driver.when.sign_in_as("uid-moshe")
    assert await driver.get.titles() == ["Moshe's own", "Who are my clients?"]
    opened = await driver.get.conversation(name_of(CLIENTS))
    assert opened is not None and opened[0].title == "Who are my clients?"


async def test_refuses_invalid_input_and_keeps_the_conversation(
    driver: ConversationsDriver,
) -> None:
    driver.when.sign_in_as("uid-dana")
    await driver.when.say(CLIENTS, "Who are my clients?")
    await driver.when.rename(name_of(CLIENTS), "Dana's clients")

    for title, paths in [
        ("", ["title"]),
        ("   ", ["title"]),
        ("x" * 101, ["title"]),
        ("Taken", ["name"]),
        ("Taken", []),
    ]:
        await driver.when.update(name_of(CLIENTS), title=title, paths=paths)
        assert driver.get.error() == Code.INVALID_ARGUMENT, (title, paths)
    await driver.when.rename("conversations/" + CLIENTS, "Taken")
    assert driver.get.error() == Code.INVALID_ARGUMENT
    for parent, page_size in [("users/uid-dana", 0), ("agents/assistant", -1)]:
        assert await driver.get.conversations(parent, page_size=page_size) is None
        assert driver.get.error() == Code.INVALID_ARGUMENT, (parent, page_size)

    # Names that start right but name no conversation.
    for name in [
        "agents/assistant/conversations/not-a-uuid",
        f"agents/Not An Agent/conversations/{CLIENTS}",
        f"agents/assistant/threads/{CLIENTS}",
        f"agents/assistant/conversations/{CLIENTS}/more",
        "agents/assistant",
    ]:
        assert await driver.get.conversation(name) is None
        assert driver.get.error() == Code.NOT_FOUND, name
        await driver.when.rename(name, "Taken")
        assert driver.get.error() == Code.NOT_FOUND, name

    assert await driver.get.titles() == ["Dana's clients"]
    await driver.when.rename(name_of(CLIENTS), "Clients")
    assert await driver.get.titles() == ["Clients"]

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from libs.infra.filtering.filtering import FilterSchema, InvalidFilterError


class Nickname(sa.TypeDecorator[str]):
    """A wrapper type, like SQLModel's string type, which reports `object` as its Python type."""

    impl = sa.String
    cache_ok = True


metadata = sa.MetaData()
people = sa.Table(
    "people",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("first_name", sa.String(), nullable=False),
    sa.Column("last_name", sa.String(), nullable=False),
    sa.Column("email", sa.String(), nullable=True),
    sa.Column("nickname", Nickname(), nullable=False),
    sa.Column("age", sa.Integer(), nullable=False),
    sa.Column("joined", sa.DateTime(timezone=True), nullable=False),
)
cities = sa.Table(
    "cities",
    metadata,
    sa.Column("person_id", sa.Uuid(), primary_key=True),
    sa.Column("name", sa.String(), nullable=False),
)

AVI = UUID("00000000-0000-0000-0000-000000000001")
NOA = UUID("00000000-0000-0000-0000-000000000002")
DANA = UUID("00000000-0000-0000-0000-000000000003")

# The API calls the column `last_name` "family_name", and offers a computed and a joined path.
schema = FilterSchema(
    {
        "first_name": people.c.first_name,
        "family_name": people.c.last_name,
        "full_name": sa.func.concat(people.c.first_name, " ", people.c.last_name),
        "email": people.c.email,
        "nickname": people.c.nickname,
        "age": people.c.age,
        "joined": people.c.joined,
        "id": people.c.id,
        "city/name": cities.c.name,
    }
)


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)
        await connection.run_sync(metadata.create_all)
        await connection.execute(
            people.insert(),
            [
                {
                    "id": AVI,
                    "first_name": "Avi",
                    "last_name": "Cohen",
                    "nickname": "avico",
                    "email": "avi@example.com",
                    "age": 41,
                    "joined": datetime(2025, 3, 1, tzinfo=UTC),
                },
                {
                    "id": NOA,
                    "first_name": "Noa",
                    "last_name": "Bar",
                    "nickname": "noab",
                    "email": None,
                    "age": 29,
                    "joined": datetime(2026, 2, 1, tzinfo=UTC),
                },
                {
                    "id": DANA,
                    "first_name": "Dana",
                    "last_name": "Levi",
                    "nickname": "dl",
                    "email": "dana@example.com",
                    "age": 35,
                    "joined": datetime(2026, 7, 1, tzinfo=UTC),
                },
            ],
        )
        await connection.execute(
            cities.insert(),
            [{"person_id": AVI, "name": "Haifa"}, {"person_id": NOA, "name": "Tel Aviv"}],
        )
    yield engine
    await engine.dispose()


async def matching(engine: AsyncEngine, filter: str) -> list[str]:
    query = (
        sa.select(people.c.first_name)
        .select_from(people.outerjoin(cities, cities.c.person_id == people.c.id))
        .where(schema.where(filter))
        .order_by(people.c.first_name)
    )
    async with engine.connect() as connection:
        return list((await connection.execute(query)).scalars())


@pytest.mark.parametrize(
    ("filter", "names"),
    [
        ("first_name eq 'Avi'", ["Avi"]),
        ("first_name ne 'Avi'", ["Dana", "Noa"]),
        ("age gt 35", ["Avi"]),
        ("age ge 35", ["Avi", "Dana"]),
        ("age lt 35", ["Noa"]),
        ("age le 35", ["Dana", "Noa"]),
        ("age gt 30 and age lt 40", ["Dana"]),
        ("age lt 30 or age gt 40", ["Avi", "Noa"]),
        ("not (age gt 30)", ["Noa"]),
        ("first_name in ('Avi', 'Noa')", ["Avi", "Noa"]),
        ("contains(first_name, 'an')", ["Dana"]),
        ("startswith(first_name, 'No')", ["Noa"]),
        ("endswith(first_name, 'vi')", ["Avi"]),
        ("email eq null", ["Noa"]),
        ("email ne null", ["Avi", "Dana"]),
        ("joined gt 2026-01-01T00:00:00Z", ["Dana", "Noa"]),
        ("id eq 00000000-0000-0000-0000-000000000003", ["Dana"]),
        ("family_name eq 'Levi'", ["Dana"]),
        ("full_name eq 'Noa Bar'", ["Noa"]),
        ("city/name eq 'Haifa'", ["Avi"]),
        ("first_name eq family_name", []),
        ("35 lt age", ["Avi"]),
        ("nickname eq 'noab'", ["Noa"]),
    ],
)
async def test_turns_a_filter_into_a_query(
    engine: AsyncEngine, filter: str, names: list[str]
) -> None:
    assert await matching(engine, filter) == names


@pytest.mark.parametrize(
    ("filter", "problem"),
    [
        ("first_name eq", "not a valid filter"),
        ("last_name eq 'Levi'", "unknown field 'last_name'"),
        ("city/zip eq '31000'", "unknown field 'city/zip'"),
        ("age eq 'old'", "'age' holds whole numbers"),
        ("first_name eq 42", "'first_name' holds text"),
        ("nickname eq 42", "'nickname' holds text"),
        ("joined gt 'yesterday'", "'joined' holds date-times"),
        ("first_name in ('Avi', 3)", "'first_name' holds text"),
        ("first_name eq age", "'first_name' and 'age' hold different types"),
        ("contains(age, '4')", "contains needs a text field"),
        ("tolower(first_name) eq 'avi'", "tolower is not supported"),
        ("age add 1 gt 40", "arithmetic is not supported"),
        ("'Avi' eq 'Avi'", "compare a field"),
    ],
)
def test_rejects_an_invalid_filter_and_says_why(filter: str, problem: str) -> None:
    with pytest.raises(InvalidFilterError, match=problem) as invalid:
        schema.where(filter)

    assert invalid.value.valid_paths == sorted(schema.paths)

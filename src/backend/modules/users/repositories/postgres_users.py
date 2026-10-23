from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from modules.users.domain.user import User


class UserRow(SQLModel, table=True):
    """What a user changed about themselves. The sign-in provider owns the rest, such as the
    email, so every sign-in brings it."""

    # SQLModel types __tablename__ as declared_attr, though it accepts a plain string.
    __tablename__ = "users"  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]
    __table_args__ = {"schema": "users"}

    id: str = Field(primary_key=True)
    display_name: str


class PostgresUserRepository:
    def __init__(self, database: AsyncEngine) -> None:
        self._database = database

    async def with_saved_changes(self, user: User) -> User:
        async with AsyncSession(self._database) as session:
            row = await session.get(UserRow, user.id)
        if row is None:
            return user
        return user.model_copy(update={"display_name": row.display_name})

    async def save(self, user: User) -> None:
        row = UserRow.model_validate(user)
        upsert = (
            insert(UserRow)
            .values(**row.model_dump())
            .on_conflict_do_update(index_elements=["id"], set_={"display_name": row.display_name})
        )
        async with self._database.begin() as connection:
            await connection.execute(upsert)

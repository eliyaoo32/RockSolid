from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, tuple_
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Field, SQLModel, col, delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from libs.infra.db.transaction import BeforeCommit
from libs.infra.filtering.filtering import FilterSchema
from modules.clients.domain.client import Client
from modules.users.domain.user import UserId


class ClientRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr, though it accepts a plain string.
    __tablename__ = "clients"  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]
    __table_args__ = {"schema": "clients"}

    id: UUID = Field(primary_key=True)
    owner_id: str = Field(index=True)
    display_name: str
    email: str | None
    create_time: datetime = Field(sa_type=DateTime(timezone=True))
    update_time: datetime = Field(sa_type=DateTime(timezone=True))


# What ListClients can filter on. The API names match the column names.
CLIENT_FILTERS = FilterSchema(
    {
        "display_name": col(ClientRow.display_name),
        "email": col(ClientRow.email),
        "create_time": col(ClientRow.create_time),
        "update_time": col(ClientRow.update_time),
    }
)


class PostgresClientRepository:
    def __init__(self, database: AsyncEngine) -> None:
        self._database = database

    async def get(self, owner_id: UserId, client_id: UUID) -> Client | None:
        async with AsyncSession(self._database) as session:
            row = await session.get(ClientRow, client_id)
        if row is None or row.owner_id != owner_id:
            return None
        return Client.model_validate(row, from_attributes=True)

    async def list_newest_first(
        self, owner_id: UserId, limit: int, after: tuple[datetime, UUID] | None, filter: str
    ) -> list[Client]:
        query = select(ClientRow).where(ClientRow.owner_id == owner_id)
        if filter:
            query = query.where(CLIENT_FILTERS.where(filter))
        if after is not None:
            query = query.where(tuple_(col(ClientRow.create_time), col(ClientRow.id)) < after)
        query = query.order_by(col(ClientRow.create_time).desc(), col(ClientRow.id).desc())
        async with AsyncSession(self._database) as session:
            rows = await session.exec(query.limit(limit))
            return [Client.model_validate(row, from_attributes=True) for row in rows]

    async def count_created_since(self, since: datetime) -> int:
        query = (
            select(func.count()).select_from(ClientRow).where(col(ClientRow.create_time) >= since)
        )
        async with AsyncSession(self._database) as session:
            return (await session.exec(query)).one()

    async def save(self, client: Client, before_commit: BeforeCommit | None = None) -> None:
        async with AsyncSession(self._database) as session:
            await session.merge(ClientRow.model_validate(client, from_attributes=True))
            if before_commit is not None:
                await before_commit(await session.connection())
            await session.commit()

    async def delete(self, owner_id: UserId, client_id: UUID) -> bool:
        query = delete(ClientRow).where(
            col(ClientRow.id) == client_id, col(ClientRow.owner_id) == owner_id
        )
        async with AsyncSession(self._database) as session:
            result = await session.exec(query)
            await session.commit()
        return result.rowcount == 1

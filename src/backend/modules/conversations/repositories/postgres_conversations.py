from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Field, SQLModel, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from modules.conversations.domain.conversation import ActiveRun, Conversation, ConversationKey


class ConversationRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr, though it accepts a plain string.
    __tablename__ = "conversations"  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]
    __table_args__ = {"schema": "conversations"}

    id: UUID = Field(primary_key=True)
    key_agent: str
    key_owner_id: str | None
    key_thread_id: UUID
    history: str = Field(sa_type=Text)
    active_run_run_id: UUID | None
    active_run_started_at: datetime | None = Field(sa_type=DateTime(timezone=True))
    create_time: datetime = Field(sa_type=DateTime(timezone=True))
    update_time: datetime = Field(sa_type=DateTime(timezone=True))


class PostgresConversationRepository:
    def __init__(self, database: AsyncEngine) -> None:
        self._database = database

    async def change[T](
        self,
        key: ConversationKey,
        new: Conversation,
        change: Callable[[Conversation], T],
    ) -> T:
        add_unless_present = (
            insert(ConversationRow).values(**_to_row(new).model_dump()).on_conflict_do_nothing()
        )
        load_locked = (
            select(ConversationRow)
            .where(
                col(ConversationRow.key_agent) == key.agent,
                col(ConversationRow.key_owner_id).is_not_distinct_from(key.owner_id),
                col(ConversationRow.key_thread_id) == key.thread_id,
            )
            .with_for_update()
        )
        async with AsyncSession(self._database) as session:
            await session.exec(add_unless_present)
            row = (await session.exec(load_locked)).one()
            conversation = _to_conversation(row)
            result = change(conversation)
            row.sqlmodel_update(_to_row(conversation).model_dump(exclude={"id"}))
            session.add(row)
            await session.commit()
        return result


def _to_row(conversation: Conversation) -> ConversationRow:
    active_run = conversation.active_run
    return ConversationRow(
        id=conversation.id,
        key_agent=conversation.key.agent,
        key_owner_id=conversation.key.owner_id,
        key_thread_id=conversation.key.thread_id,
        history=conversation.history,
        active_run_run_id=None if active_run is None else active_run.run_id,
        active_run_started_at=None if active_run is None else active_run.started_at,
        create_time=conversation.create_time,
        update_time=conversation.update_time,
    )


def _to_conversation(row: ConversationRow) -> Conversation:
    active_run = (
        None
        if row.active_run_run_id is None or row.active_run_started_at is None
        else ActiveRun(run_id=row.active_run_run_id, started_at=row.active_run_started_at)
    )
    return Conversation(
        id=row.id,
        key=ConversationKey(
            agent=row.key_agent, owner_id=row.key_owner_id, thread_id=row.key_thread_id
        ),
        history=row.history,
        active_run=active_run,
        create_time=row.create_time,
        update_time=row.update_time,
    )

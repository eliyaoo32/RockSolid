from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic_ai.messages import ModelMessagesTypeAdapter
from sqlalchemy import ColumnElement, DateTime, tuple_
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Field, SQLModel, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from modules.conversations.domain.conversation import AgentName, Conversation, ConversationKey
from modules.conversations.services.errors import ConversationNotFoundError
from modules.users.domain.user import UserId


class ConversationRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr, though it accepts a plain string.
    __tablename__ = "conversations"  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]
    __table_args__ = {"schema": "conversations"}

    id: UUID = Field(primary_key=True)
    key_agent: str
    key_owner_id: str | None
    key_thread_id: UUID
    # The messages in Pydantic AI's JSON form.
    messages: list[dict[str, Any]] = Field(sa_type=JSONB)
    run_started_at: datetime | None = Field(sa_type=DateTime(timezone=True))
    title: str | None
    pinned: bool
    last_message_time: datetime | None = Field(sa_type=DateTime(timezone=True))
    create_time: datetime = Field(sa_type=DateTime(timezone=True))
    update_time: datetime = Field(sa_type=DateTime(timezone=True))


class PostgresConversationRepository:
    def __init__(self, database: AsyncEngine) -> None:
        self._database = database

    async def change[T](
        self,
        key: ConversationKey,
        new: Conversation | None,
        change: Callable[[Conversation], T],
    ) -> T:
        load_locked = select(ConversationRow).where(*_has_key(key)).with_for_update()
        async with AsyncSession(self._database) as session:
            if new is not None:
                add_unless_present = (
                    insert(ConversationRow)
                    .values(**_to_row(new).model_dump())
                    .on_conflict_do_nothing()
                )
                await session.exec(add_unless_present)
            row = (await session.exec(load_locked)).one_or_none()
            if row is None:
                raise ConversationNotFoundError
            conversation = _to_conversation(row)
            result = change(conversation)
            row.sqlmodel_update(_to_row(conversation).model_dump(exclude={"id"}))
            session.add(row)
            await session.commit()
        return result

    async def get(self, key: ConversationKey) -> Conversation | None:
        async with AsyncSession(self._database) as session:
            row = (await session.exec(select(ConversationRow).where(*_has_key(key)))).one_or_none()
        return None if row is None else _to_conversation(row)

    async def list_pinned_first(
        self,
        agent: AgentName,
        owner_id: UserId,
        limit: int,
        after: tuple[bool, datetime, UUID] | None,
    ) -> list[Conversation]:
        position = tuple_(
            col(ConversationRow.pinned),
            col(ConversationRow.last_message_time),
            col(ConversationRow.id),
        )
        query = select(ConversationRow).where(
            col(ConversationRow.key_agent) == agent,
            col(ConversationRow.key_owner_id) == owner_id,
            col(ConversationRow.last_message_time).is_not(None),
        )
        if after is not None:
            query = query.where(position < after)
        query = query.order_by(
            col(ConversationRow.pinned).desc(),
            col(ConversationRow.last_message_time).desc(),
            col(ConversationRow.id).desc(),
        )
        async with AsyncSession(self._database) as session:
            rows = await session.exec(query.limit(limit))
            return [_to_conversation(row) for row in rows]


def _has_key(key: ConversationKey) -> list[ColumnElement[bool]]:
    return [
        col(ConversationRow.key_agent) == key.agent,
        col(ConversationRow.key_owner_id).is_not_distinct_from(key.owner_id),
        col(ConversationRow.key_thread_id) == key.thread_id,
    ]


def _to_row(conversation: Conversation) -> ConversationRow:
    return ConversationRow(
        id=conversation.id,
        key_agent=conversation.key.agent,
        key_owner_id=conversation.key.owner_id,
        key_thread_id=conversation.key.thread_id,
        messages=ModelMessagesTypeAdapter.dump_python(conversation.messages, mode="json"),
        run_started_at=conversation.run_started_at,
        title=conversation.title,
        pinned=conversation.pinned,
        last_message_time=conversation.last_message_time,
        create_time=conversation.create_time,
        update_time=conversation.update_time,
    )


def _to_conversation(row: ConversationRow) -> Conversation:
    return Conversation(
        id=row.id,
        key=ConversationKey(
            agent=row.key_agent, owner_id=row.key_owner_id, thread_id=row.key_thread_id
        ),
        messages=ModelMessagesTypeAdapter.validate_python(row.messages),
        run_started_at=row.run_started_at,
        title=row.title,
        pinned=row.pinned,
        last_message_time=row.last_message_time,
        create_time=row.create_time,
        update_time=row.update_time,
    )

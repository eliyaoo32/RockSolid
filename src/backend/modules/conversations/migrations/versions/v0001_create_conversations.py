"""Creates the conversations table."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key_agent", sa.String, nullable=False),
        sa.Column("key_owner_id", sa.String, nullable=True),
        sa.Column("key_thread_id", sa.Uuid(), nullable=False),
        sa.Column("history", sa.Text, nullable=False),
        sa.Column("active_run_run_id", sa.Uuid(), nullable=True),
        sa.Column("active_run_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=False),
        # One conversation per key; an anonymous one (no owner) is unique by agent and thread too.
        sa.UniqueConstraint(
            "key_agent",
            "key_owner_id",
            "key_thread_id",
            name="conversations_by_key",
            postgresql_nulls_not_distinct=True,
        ),
        schema="conversations",
    )

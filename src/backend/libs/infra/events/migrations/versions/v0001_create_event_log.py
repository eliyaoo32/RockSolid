"""Creates the event log, the subscriptions' cursors, and the parked events."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None


def upgrade() -> None:
    # Every published event, in order. Kept forever for now.
    op.create_table(
        "log",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="events",
    )
    # Serves each subscription's read: the next event of its type after its cursor.
    op.create_index("log_by_type", "log", ["type", "id"], schema="events")
    op.create_table(
        "subscriptions",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("last_event_id", sa.BigInteger(), nullable=False),
        sa.Column("failed_event_id", sa.BigInteger(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_at", sa.DateTime(timezone=True), nullable=True),
        schema="events",
    )
    op.create_table(
        "parked",
        sa.Column("subscription", sa.String(), primary_key=True),
        sa.Column("event_id", sa.BigInteger(), primary_key=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column(
            "parked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="events",
    )

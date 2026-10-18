"""Creates the queue of tasks waiting to run, and the parked tasks that stopped retrying."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None


def upgrade() -> None:
    # A task stays here until it runs or is parked.
    op.create_table(
        "queue",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        # Set after a failure: the task waits until then before its next attempt.
        sa.Column("retry_at", sa.DateTime(timezone=True), nullable=True),
        schema="tasks",
    )
    # Serves each handler's read: the oldest task of its type.
    op.create_index("queue_by_type", "queue", ["type", "id"], schema="tasks")
    op.create_table(
        "parked",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column(
            "parked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="tasks",
    )

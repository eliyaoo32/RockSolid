"""Creates the clients table."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String, nullable=False),
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=False),
        schema="clients",
    )
    # Serves ListClients: one owner's clients, newest first.
    op.create_index(
        "clients_by_owner_newest_first",
        "clients",
        ["owner_id", sa.text("create_time DESC"), sa.text("id DESC")],
        schema="clients",
    )

"""Adds what the list of conversations shows: each conversation's title, whether it is pinned,
and when its last message was added. Existing conversations get them from their messages."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"

# Titles each existing conversation with its first user text, the way the domain does: spaces
# collapsed, and cut to 100 characters with an ellipsis. Only plain-text prompts are read; a
# conversation whose prompts all carry files gets its title from the user's next message.
TITLE_FROM_FIRST_USER_TEXT = r"""
UPDATE conversations.conversations AS c
SET title = CASE
    WHEN length(earliest.text) <= 100 THEN earliest.text
    ELSE rtrim(left(earliest.text, 99)) || '…'
END
FROM (
    SELECT DISTINCT ON (existing.id) existing.id, prompt.text
    FROM conversations.conversations AS existing,
        jsonb_array_elements(existing.messages) WITH ORDINALITY AS message(value, position),
        jsonb_array_elements(message.value -> 'parts') WITH ORDINALITY AS part(value, position),
        LATERAL (
            SELECT btrim(regexp_replace(part.value ->> 'content', '\s+', ' ', 'g')) AS text
        ) AS prompt
    WHERE part.value ->> 'part_kind' = 'user-prompt'
        AND jsonb_typeof(part.value -> 'content') = 'string'
        AND prompt.text <> ''
    ORDER BY existing.id, message.position, part.position
) AS earliest
WHERE c.id = earliest.id
"""


def upgrade() -> None:
    op.add_column(
        "conversations", sa.Column("title", sa.String, nullable=True), schema="conversations"
    )
    op.add_column(
        "conversations",
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        schema="conversations",
    )
    op.add_column(
        "conversations",
        sa.Column("last_message_time", sa.DateTime(timezone=True), nullable=True),
        schema="conversations",
    )
    # Every message so far was added at or before the conversation's last change.
    op.execute(
        "UPDATE conversations.conversations SET last_message_time = update_time"
        " WHERE jsonb_array_length(messages) > 0"
    )
    op.execute(TITLE_FROM_FIRST_USER_TEXT)

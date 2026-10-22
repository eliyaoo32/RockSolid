"""Applies the users migrations to the connection the caller passes in `attributes`."""

from alembic import context
from sqlalchemy import Connection, text

connection: Connection = context.config.attributes["connection"]
# Several replicas may start at once; the lock lets one migrate while the others wait.
connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('users'))"))
connection.execute(text("CREATE SCHEMA IF NOT EXISTS users"))
context.configure(connection=connection, version_table_schema="users")
with context.begin_transaction():
    context.run_migrations()

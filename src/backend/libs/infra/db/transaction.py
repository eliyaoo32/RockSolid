"""The transaction a repository saves in, which other writes can join to commit with it."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncConnection

# An open transaction. What is written in it commits together, or not at all.
type Transaction = AsyncConnection
# Writes more in a save's transaction, such as the events and tasks the change produces.
type BeforeCommit = Callable[[Transaction], Awaitable[None]]

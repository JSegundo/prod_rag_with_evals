import asyncpg
from pgvector.asyncpg import register_vector

from app.config import settings


pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global pool
    pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=10,
        init=_init_connection,
    )
    # Verify database is reachable
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
    return pool


async def _init_connection(conn: asyncpg.Connection):
    await register_vector(conn)


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    return pool


async def execute_query(
    query: str,
    params: list | None = None,
    fetch_one: bool = False,
):
    p = get_pool()
    async with p.acquire() as conn:
        if fetch_one:
            return await conn.fetchrow(query, *(params or []))
        return await conn.fetch(query, *(params or []))


async def execute_command(query: str, params: list | None = None):
    """Execute a query that doesn't return rows (INSERT, UPDATE, DELETE)."""
    p = get_pool()
    async with p.acquire() as conn:
        return await conn.execute(query, *(params or []))

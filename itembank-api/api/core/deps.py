"""
Dependency injection for FastAPI.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg

from .config import Settings, get_settings

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool(settings: Settings) -> asyncpg.Pool:
    """Initialize database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=settings.db_pool_size,
        )
    return _pool


async def close_db_pool() -> None:
    """Close database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn

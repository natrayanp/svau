# utils/database/database_async.py
import os
from functools import lru_cache

from utils.database.database_async_core import AsyncDatabaseManager


@lru_cache()
def get_db_manager() -> AsyncDatabaseManager:
    """
    Singleton async DB manager with RW1 (optional read-replica).

    Env:
      - DATABASE_URL: write DSN (required)
      - READ_REPLICA_URL: read DSN (optional)
    """
    write_dsn = os.getenv("DATABASE_URL")
    read_dsn = os.getenv("READ_REPLICA_URL")  # optional

    if not write_dsn:
        raise RuntimeError("DATABASE_URL is not set")

    return AsyncDatabaseManager(
        write_dsn=write_dsn,
        read_dsn=read_dsn,
        min_pool_size=2,
        max_pool_size=10,
        slow_query_ms=200,
        retries=3,
    )


async def get_db() -> AsyncDatabaseManager:
    """
    FastAPI dependency.

    Usage:
        @router.get("/something")
        async def handler(db = Depends(get_db)):
            row = await db.fetch_one_async("SELECT 1")
    """
    return get_db_manager()

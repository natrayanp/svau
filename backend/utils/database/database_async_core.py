# utils/database/database_async_core.py
import asyncpg
import logging
import time
import re
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
import re
import json

logger = logging.getLogger(__name__)
# ============================================================
# JSON PARSING HELPERS
# ============================================================

def _maybe_parse_json(value):
    if value is None:
        return None

    # asyncpg already returns JSONB as dict/list when possible
    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):
        v = value.strip()
        if not v:
            return value

        # Only attempt JSON parsing if the string *looks* like JSON
        if v[0] in ("{", "["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return value

    return value



# ============================================================
# Named parameter conversion: %(name)s → $1, $2, $3
# ============================================================

_named_param_pattern = re.compile(r"%\(([^)]+)\)s")
#_positional_pattern = re.compile(r"%s")

def _convert_params(query: str, params: Dict[str, Any]):
    """
    Convert psycopg2-style %(name)s placeholders into asyncpg-style $1, $2, ...
    Handles repeated named placeholders correctly.
    """
    if not params:
        return query, []

    names = _named_param_pattern.findall(query)

    # Maintain order of first appearance
    seen = {}
    positional_params = []
    index = 1

    for name in names:
        if name not in seen:
            if name not in params:
                raise KeyError(f"Missing parameter: {name}")
            seen[name] = index
            positional_params.append(params[name])
            index += 1

    # Replace each placeholder with its assigned $index
    for name, idx in seen.items():
        query = query.replace(f"%({name})s", f"${idx}")

    return query, positional_params


# ============================================================


class AsyncDatabaseError(Exception):
    """Custom exception for async database errors."""
    def __init__(self, message: str, query: str | None = None):
        super().__init__(message)
        self.message = message
        self.query = query


class AsyncDatabaseManager:
    """
    Enterprise-grade async DB manager with:
    - asyncpg connection pooling
    - async transactions
    - optional read/write splitting
    - retry logic
    - slow query logging
    """

    def __init__(
        self,
        write_dsn: str,
        read_dsn: Optional[str] = None,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        slow_query_ms: int = 200,
        retries: int = 3,
    ):
        self.write_dsn = write_dsn
        self.read_dsn = read_dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.slow_query_ms = slow_query_ms
        self.retries = retries

        self.write_pool: Optional[asyncpg.Pool] = None
        self.read_pool: Optional[asyncpg.Pool] = None

    # ------------------------------------------------------
    # INIT POOLS
    # ------------------------------------------------------
    async def connect(self):
        """Initialize write pool and optional read pool."""
        if not self.write_pool:
            self.write_pool = await asyncpg.create_pool(
                dsn=self.write_dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=30,
            )
            logger.info("✅ Async write pool initialized")

        if self.read_dsn and not self.read_pool:
            self.read_pool = await asyncpg.create_pool(
                dsn=self.read_dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=30,
            )
            logger.info("✅ Async read pool initialized")

    async def close(self):
        """Close pools on shutdown if needed."""
        if self.write_pool:
            await self.write_pool.close()
            self.write_pool = None
        if self.read_pool:
            await self.read_pool.close()
            self.read_pool = None

    # ------------------------------------------------------
    # POOL SELECTION (RW1)
    # ------------------------------------------------------
    def _get_pool(self, write: bool) -> asyncpg.Pool:
        """
        RW1 mode:
        - If write=True → always use write pool.
        - If write=False → use read pool if configured, else write pool.
        """
        if write or not self.read_pool:
            if not self.write_pool:
                raise AsyncDatabaseError("Write pool not initialized")
            return self.write_pool

        if not self.read_pool:
            raise AsyncDatabaseError("Read pool requested but not initialized")

        return self.read_pool

    # ------------------------------------------------------
    # TRANSACTION MANAGER (WRITE)
    # ------------------------------------------------------
    @asynccontextmanager
    async def transaction_async(self):
        """
        Async transaction using the write pool.

        Usage:
            async with db.transaction_async():
                await db.execute_async(...)
                await db.execute_async(...)
        """
        await self.connect()
        pool = self._get_pool(write=True)

        async with pool.acquire() as conn:
            tx = conn.transaction()
            await tx.start()
            try:
                yield conn
                await tx.commit()
            except Exception:
                await tx.rollback()
                raise

    # ------------------------------------------------------
    # INTERNAL EXECUTOR WITH RETRIES + LOGGING
    # ------------------------------------------------------
    async def _execute(
        self,
        query: str,
        params: Optional[Any],
        fetch: str,
        write: bool,
    ):
        """
        Internal helper:
        - fetch = "one" | "all" | "exec"
        - write = True for write queries / transactions
        """

        await self.connect()
        pool = self._get_pool(write=write)

        # Normalize params via converter for psycopg2-style queries
        if params is not None:
            query, params = _convert_params(query, params)
        else:
            params = []

        for attempt in range(1, self.retries + 1):
            try:
                start = time.time()

                async with pool.acquire() as conn:
                    stmt = await conn.prepare(query)

                    if fetch == "one":
                        row = await stmt.fetchrow(*params)
                        result = {k: _maybe_parse_json(v) for k, v in dict(row).items()} if row else None

                    elif fetch == "all":
                        rows = await stmt.fetch(*params)
                        result = [
                            {k: _maybe_parse_json(v) for k, v in dict(r).items()}
                            for r in rows
                        ]
                    else:  # "exec"
                        result = await stmt.fetch(*params)
                        return result
                        #result = True

                duration = (time.time() - start) * 1000
                if duration > self.slow_query_ms:
                    logger.warning(f"🐢 Slow query ({duration:.2f}ms): {query}")

                return result

            except Exception as e:
                logger.error(
                    f"DB error (attempt {attempt}/{self.retries}): {e} | Query: {query}"
                )
                if attempt == self.retries:
                    raise AsyncDatabaseError(str(e), query=query)


    # ------------------------------------------------------
    # PUBLIC METHODS – READ
    # ------------------------------------------------------
    async def fetch_one_async(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Read query, prefers read pool if configured.
        """
        return await self._execute(query, params, fetch="one", write=False)

    async def fetch_all_async(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Read query, prefers read pool if configured.
        """
        return await self._execute(query, params, fetch="all", write=False)

    # ------------------------------------------------------
    # PUBLIC METHODS – WRITE
    # ------------------------------------------------------
    async def execute_async(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Write query without RETURNING.
        """
        return await self._execute(query, params, fetch="exec", write=True)

    async def execute_returning_async(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Write query that returns a single row (RETURNING ...).
        """
        return await self._execute(query, params, fetch="one", write=True)

    async def execute_many_returning_async(self, query: str, values: List[tuple]):
        """
        Bulk insert with RETURNING using a single prepared statement.

        `query` should be something like:
            INSERT INTO table (a, b, c)
            VALUES ($1, $2, $3)
            RETURNING ...

        And `values` a list of tuples:
            [(a1, b1, c1), (a2, b2, c2), ...]
        """
        await self.connect()
        pool = self._get_pool(write=True)

        async with pool.acquire() as conn:
            stmt = await conn.prepare(query)

            rows = []
            for v in values:
                row = await stmt.fetchrow(*v)
                if row:
                    rows.append(dict(row))

        return rows

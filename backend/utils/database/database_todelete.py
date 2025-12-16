# utils/database/database.py
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from functools import lru_cache
from typing import List, Dict, Any, Optional, Generator, Callable
import logging
import asyncio

from utils.appwide.request_context import get_request_id

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database errors."""
    def __init__(self, message: str, query: str = None):
        super().__init__(message)
        self.message = message
        self.query = query


class DatabaseManager:
    """Manages database connections and queries with transaction support."""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self._connection = None
        self._transaction_depth = 0

    def _get_connection(self):
        """Get or create a connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(self.db_url)
            self._connection.autocommit = False
        return self._connection

    def close(self):
        """Close the connection if open."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        Usage:
            with db.transaction():
                db.execute("...")
                db.execute("...")
        """
        conn = self._get_connection()
        try:
            if self._transaction_depth == 0:
                logger.debug("Starting database transaction")
            
            self._transaction_depth += 1
            yield conn
            
            if self._transaction_depth == 1:
                conn.commit()
                logger.debug("Transaction committed")
            self._transaction_depth -= 1
            
        except Exception as e:
            if self._transaction_depth == 1:
                conn.rollback()
                logger.debug("Transaction rolled back")
            self._transaction_depth -= 1
            raise e
        finally:
            if self._transaction_depth == 0:
                self.close()

    @contextmanager
    def connection(self):
        """Context manager for single connection (non-transactional)."""
        conn = self._get_connection()
        try:
            yield conn
        finally:
            pass  # Don't close here, let transaction handle it

    def _execute_in_context(self, query_func: Callable, query: str, params: Optional[dict] = None, fetch: bool = False):
        """Helper to execute queries in the appropriate context."""
        if self._transaction_depth > 0:
            # Already in a transaction, use existing connection
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                return query_func(cursor, query, params, fetch)
        else:
            # Not in a transaction, create a new one
            with self.transaction() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    return query_func(cursor, query, params, fetch)

    def _execute_cursor(self, cursor, query: str, params: Optional[dict] = None, fetch: bool = False):
        """Execute query on cursor."""
        try:
            cursor.execute(query, params)
            if fetch:
                if "RETURNING" in query.upper():
                    row = cursor.fetchone()
                    if row:
                        result = dict(row)
                        logger.debug(f"RETURNING row: {result}, type={type(result)}")
                        return result
                    return None
                else:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
            return cursor.rowcount
        except psycopg2.Error as e:
            request_id = get_request_id()
            logger.error(f"[{request_id}] DB error: {e} - Query: {query}")
            raise DatabaseError(str(e), query=query)

    def fetch_all(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Fetch multiple rows."""
        result = self._execute_in_context(self._execute_cursor, query, params, fetch=True)
        return result if isinstance(result, list) else []

    def fetch_one(self, query: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Fetch single row."""
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def execute(self, query: str, params: Optional[dict] = None) -> int:
        """Execute INSERT/UPDATE/DELETE, returning affected row count."""
        result = self._execute_in_context(self._execute_cursor, query, params, fetch=False)
        return result if isinstance(result, int) else 0

    def execute_returning(self, query: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Execute query with RETURNING clause."""
        result = self._execute_in_context(self._execute_cursor, query, params, fetch=True)
        return result if isinstance(result, dict) else None

    def execute_many(self, queries: List[tuple]) -> List[int]:
        """Execute multiple queries in a single transaction."""
        results = []
        with self.transaction():
            for query, params in queries:
                result = self.execute(query, params)
                results.append(result)
        return results

    def execute_in_transaction(self, operation_func: Callable, *args, **kwargs):
        """
        Execute a function within a transaction.
        
        Usage:
            def update_role_operation(db, role_id, data):
                db.execute("UPDATE roles ...", {"role_id": role_id})
                db.execute("INSERT INTO logs ...", {"role_id": role_id})
            
            db.execute_in_transaction(update_role_operation, role_id, data)
        """
        with self.transaction():
            return operation_func(self, *args, **kwargs)

    # =================== ASYNC METHODS ===================
    # These wrap synchronous DB calls to be non-blocking
    
    async def fetch_all_async(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Async fetch multiple rows."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_all_sync, query, params)

    async def fetch_one_async(self, query: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Async fetch single row."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_one_sync, query, params)

    async def execute_async(self, query: str, params: Optional[dict] = None) -> int:
        """Async execute INSERT/UPDATE/DELETE."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, query, params)

    async def execute_returning_async(self, query: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Async execute query with RETURNING clause."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_returning_sync, query, params)
    
    # Internal sync methods (renamed to avoid conflicts)
    def _fetch_all_sync(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Synchronous fetch_all."""
        result = self._execute_in_context(self._execute_cursor, query, params, fetch=True)
        return result if isinstance(result, list) else []

    def _fetch_one_sync(self, query: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Synchronous fetch_one."""
        rows = self._fetch_all_sync(query, params)
        return rows[0] if rows else None

    def _execute_sync(self, query: str, params: Optional[dict] = None) -> int:
        """Synchronous execute."""
        result = self._execute_in_context(self._execute_cursor, query, params, fetch=False)
        return result if isinstance(result, int) else 0

    def _execute_returning_sync(self, query: str, params: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Synchronous execute_returning."""
        result = self._execute_in_context(self._execute_cursor, query, params, fetch=True)
        if isinstance(result, dict):
            return result
        elif result is not None:
            # If it's something else (shouldn't be), try to convert it
            try:
                return dict(result) if hasattr(result, '__iter__') and not isinstance(result, str) else None
            except Exception:
                return None
        return None

    async def execute_update_async(self, query: str, params: Optional[dict] = None) -> int:
        """Async execute UPDATE, alias for execute_async."""
        return await self.execute_async(query, params)


# Singleton instance
@lru_cache()
def get_db_manager():
    return DatabaseManager()


def get_db():
    """FastAPI dependency for database."""
    db = get_db_manager()
    try:
        yield db
    finally:
        db.close()
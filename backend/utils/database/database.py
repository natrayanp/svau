# utils/database/database.py

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from functools import lru_cache
from typing import List, Dict, Any, Optional
import logging

from utils.appwide.request_context import get_request_id

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database errors."""
    def __init__(self, message: str, query: str = None):
        super().__init__(message)
        self.message = message
        self.query = query


class DatabaseManager:
    """Manages database connections and queries."""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")

    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(self.db_url)
        conn.autocommit = False
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except psycopg2.Error as e:
            request_id = get_request_id()
            logger.error(f"[{request_id}] DB error in fetch_all: {e} - Query: {query}")
            raise DatabaseError(str(e), query=query)

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    return dict(row) if row else None
        except psycopg2.Error as e:
            request_id = get_request_id()
            logger.error(f"[{request_id}] DB error in fetch_one: {e} - Query: {query}")
            raise DatabaseError(str(e), query=query)

    def execute(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE, returning affected row count."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    affected = cursor.rowcount
                    conn.commit()
                    return affected
        except psycopg2.Error as e:
            request_id = get_request_id()
            logger.error(f"[{request_id}] DB error in execute: {e} - Query: {query}")
            raise DatabaseError(str(e), query=query)

    def execute_insert(self, query: str, params: Optional[tuple] = None) -> Optional[int]:
        """Execute INSERT ... RETURNING id."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    if "RETURNING" in query.upper():
                        row = cursor.fetchone()
                        inserted_id = row["id"] if row else None
                    else:
                        inserted_id = None
                    conn.commit()
                    return inserted_id
        except psycopg2.Error as e:
            request_id = get_request_id()
            logger.error(f"[{request_id}] DB error in execute_insert: {e} - Query: {query}")
            raise DatabaseError(str(e), query=query)


# Singleton instance
from functools import lru_cache

@lru_cache()
def get_db_manager():
    return DatabaseManager()


def get_db():
    return get_db_manager()

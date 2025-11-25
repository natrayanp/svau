import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from functools import lru_cache
from typing import List, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
    
    @contextmanager
    def get_connection(self):
        """Centralized connection management"""
        conn = psycopg2.connect(self.db_url)
        conn.autocommit = False
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    # CENTRALIZED EXECUTION METHODS
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        fetch: bool = False
    ) -> Union[int, List[Dict[str, Any]]]:
        """
        Execute query with centralized error handling and result formatting
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    
                    if fetch:
                        result = [dict(row) for row in cursor.fetchall()]
                        conn.commit()
                        return result
                    else:
                        conn.commit()
                        return cursor.rowcount
                        
        except psycopg2.Error as e:
            logger.error(f"Database error: {e} - Query: {query}")
            raise
    
    def execute_single(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single row
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    conn.commit()
                    return dict(row) if row else None
                    
        except psycopg2.Error as e:
            logger.error(f"Database error: {e} - Query: {query}")
            raise
    
    def execute_insert(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> int:
        """
        Execute INSERT and return inserted ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    if "RETURNING id" in query.upper():
                        result = cursor.fetchone()
                        inserted_id = result['id'] if result else None
                    else:
                        inserted_id = cursor.lastrowid
                    conn.commit()
                    return inserted_id
                    
        except psycopg2.Error as e:
            logger.error(f"Database error: {e} - Query: {query}")
            raise
    
    def execute_update(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> bool:
        """
        Execute UPDATE and return success status
        """
        try:
            rowcount = self.execute_query(query, params, fetch=False)
            return rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Database error: {e} - Query: {query}")
            raise

# Singleton instance
@lru_cache()
def get_db_manager():
    return DatabaseManager()

# FastAPI dependency
def get_db():
    return get_db_manager()
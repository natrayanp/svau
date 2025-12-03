# utils/errors.py

from typing import Optional
import logging
from utils.database.database import DatabaseManager, get_db, DatabaseError

logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    Application-specific exception with:
    - code: Unique identifier for frontend handling
    - message: Human-readable message (from DB if available)
    - details: Optional internal details for logs
    """

    def __init__(
        self,
        code: str,
        message: Optional[str] = None,
        details: Optional[str] = None,
        db: DatabaseManager = None
    ):
        self.code = code
        self.details = details
        self.message = message

        # If message is not passed, try to fetch from DB
        if not self.message:
            try:
                if db is None:
                    db = get_db()

                query = """
                SELECT message
                FROM error_messages
                WHERE code = %s
                LIMIT 1
                """
                result = db.fetch_one(query, (code,))
                if result and result.get("message"):
                    self.message = result["message"]
                else:
                    # fallback generic message
                    self.message = "An error occurred"
            except DatabaseError as e:
                logger.error(f"DB error fetching error message for code {code}: {e}")
                self.message = "An error occurred"
            except Exception as e:
                logger.exception(f"Unexpected error fetching error message for code {code}: {e}")
                self.message = "An error occurred"

        super().__init__(self.message)

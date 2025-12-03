# utils/auth/middleware.py

import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from utils.database.database import get_db, DatabaseManager, DatabaseError
from .jwt_utils import jwt_manager
from models.auth_models import User
from utils.api.api_response_middleware import get_request_id
from utils.appwide.errors import AppException

load_dotenv()

security = HTTPBearer(auto_error=False)

# Environment-based test user configuration
USE_TEST_USER = os.getenv("USE_TEST_USER", "false").lower() == "true"
TEST_USER_DATA = {
    "user_id": int(os.getenv("TEST_USER_ID", 1)),
    "uid": os.getenv("TEST_USER_UID", "test-uid"),
    "email": os.getenv("TEST_USER_EMAIL", "testuser@example.com"),
    "display_name": os.getenv("TEST_USER_FULL_NAME", "Test User"),
    "email_verified": os.getenv("TEST_USER_EMAIL_VERIFIED", "true").lower() == "true",
    "created_at": os.getenv("TEST_USER_CREATED_AT", "2025-11-30T00:00:00"),
    "org_id": int(os.getenv("TEST_USER_ORG_ID", 1)),
    "roles": os.getenv("TEST_USER_ROLES", "admin").split(",")
}
TEST_USER = User(**TEST_USER_DATA)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_db)
) -> User:
    """
    Get current user from JWT token or test user fallback.
    Logs DB errors internally, sends generic message to UI with error code.
    """
    request_id = get_request_id()

    if USE_TEST_USER and (credentials is None or not credentials.credentials):
        return TEST_USER

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException(
            message="Authorization header missing or invalid",
            code="AUTH_HEADER_INVALID"
        )

    try:
        payload = jwt_manager.verify_token(credentials.credentials)
        user_id = payload.get("user_id")
        if not user_id:
            raise AppException(
                message="Invalid token payload",
                code="AUTH_INVALID_PAYLOAD"
            )

        # Fetch user from database
        try:
            user_data = db.fetch_one(
                "SELECT id, uid, email, full_name, email_verified, created_at, organization_id, roles "
                "FROM users WHERE id = %s",
                (user_id,)
            )
        except DatabaseError as db_err:
            logger.error(
                f"[{request_id}] DatabaseError fetching user: {db_err.message}, query: {db_err.query}, "
                f"original: {db_err.original_exception}"
            )
            raise AppException(
                message="An internal error occurred",
                code="DB_FETCH_USER_ERROR"
            )

        if not user_data:
            raise AppException(
                message="Invalid credentials",
                code="AUTH_USER_NOT_FOUND"
            )

        return User(**user_data)

    except AppException:
        raise
    except Exception as ex:
        logger.exception(f"[{request_id}] Unexpected error validating credentials: {ex}")
        raise AppException(
            message="Could not validate credentials",
            code="AUTH_UNKNOWN_ERROR"
        )

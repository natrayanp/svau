# utils/auth/auth_middleware.py

import os
import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

from utils.database.database import get_db, DatabaseManager
from utils.database.query_manager import permission_query
from models.auth_models import AuthUser, UserRole
from .jwt_utils import jwt_manager
import json
from pathlib import Path


load_dotenv()

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------
# ✅ ENVIRONMENT + PRODUCTION-SAFE MOCK MODE
# ---------------------------------------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

USE_TEST_USER = (
    os.getenv("USE_TEST_USER", "false").lower() == "true"
    and ENVIRONMENT != "production"
)

if ENVIRONMENT == "production" and os.getenv("USE_TEST_USER", "").lower() == "true":
    logger.warning("⚠️ USE_TEST_USER was set to true but is DISABLED in production")
# ---------------------------------------------------------
# ✅ Load shared whitelist.json
# ---------------------------------------------------------
WHITELIST_PATH = Path(__file__).resolve().parents[2] / "shared" / "whitelist.json"

try:
    with open(WHITELIST_PATH, "r") as f:
        whitelist = json.load(f)
        PUBLIC_PATHS = set(whitelist.get("PUBLIC_PATHS", []))
        PUBLIC_PREFIXES = whitelist.get("PUBLIC_PREFIXES", [])
except Exception as e:
    # Fallback if file missing
    PUBLIC_PATHS = {
        "/auth-api/login",
        "/auth-api/register",
        "/auth-api/refresh",
        "/auth-api/logout",
        "/auth-api/health",
    }
    PUBLIC_PREFIXES = ["/auth-api/permissions"]
    print(f"⚠️ Failed to load shared whitelist.json: {e}")

# ---------------------------------------------------------
# ✅ ROLE-BASED MOCK USERS
# ---------------------------------------------------------
MOCK_USERS = {
    "admin": AuthUser(
        user_id=9991,
        uid="mock-admin",
        email="admin@example.com",
        display_name="Mock Admin",
        role=UserRole.ADMIN,
        email_verified=True,
        created_at="2025-01-01T00:00:00Z"
    ),
    "moderator": AuthUser(
        user_id=9992,
        uid="mock-moderator",
        email="moderator@example.com",
        display_name="Mock Moderator",
        role=UserRole.MODERATOR,
        email_verified=True,
        created_at="2025-01-01T00:00:00Z"
    ),
    "user": AuthUser(
        user_id=1,
        uid="mock-user",
        email="user@example.com",
        display_name="Mock User",
        role=UserRole.BASIC,
        email_verified=True,
        created_at="2025-01-01T00:00:00Z"
    ),
}

def is_public_route(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)

# ---------------------------------------------------------
# ✅ MAIN AUTH DEPENDENCY
# ---------------------------------------------------------
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_db)
) -> AuthUser:

    path = request.url.path

    # ✅ 1. PUBLIC ROUTE → return mock user if enabled
    if is_public_route(path):
        if USE_TEST_USER:
            mock_role = request.headers.get("X-Mock-Role", "user").lower()
            return MOCK_USERS.get(mock_role, MOCK_USERS["user"])
        return None

    # ✅ 2. GLOBAL MOCK MODE
    # ✅ MOCK MODE: return mock user and skip JWT entirely
    if USE_TEST_USER and ENVIRONMENT != "production":
        role = request.headers.get("X-Mock-Role", "user")
        mock_user = MOCK_USERS.get(role, MOCK_USERS["user"])
        return mock_user


    # ✅ 3. REAL AUTH REQUIRED
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    try:
        payload = jwt_manager.verify_token(credentials.credentials, token_type="access")
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        user_data = await db.fetch_one(
            permission_query("GET_USER_BY_ID"),
            (user_id,)
        )

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        return AuthUser(**user_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication service error")

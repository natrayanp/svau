from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded

from utils.auth.jwt_utils import get_jwt_manager
from utils.database.database import get_db
from utils.auth.auth_manager import get_auth_manager
from utils.auth.auth_middleware import get_current_user
from models.auth_models import (
    LoginRequest, TokenResponse, UserCreate, UserResponse,
    SuccessResponse, ResponseMessage, UserRole, AuthUser
)
from utils.database.query_manager import permission_query
from utils.appwide.rate_limiter import limiter

from routes.auth.services.user_service import UserService
from routes.auth.services.organization_service import OrganizationService
from dependencies.system_entities import get_system_entities, SystemEntities


import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-api", tags=["authentication"])


# --------------------------
# Request Models
# --------------------------

class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    email_verified: Optional[bool] = None

    class Config:
        use_enum_values = True


# --------------------------
# LOGIN
# --------------------------
@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db = Depends(get_db),
):
    try:
        auth_manager = get_auth_manager()
        auth_user = auth_manager.verify_token(login_data.firebase_token)

        user = await db.fetch_one_async(
            permission_query("GET_USER_BY_UID"),
            {"uid": auth_user.provider_id}
        )

        if not user:
            raise HTTPException(404, "User not registered")

        if not user.get("is_active", True):
            raise HTTPException(401, "Account is disabled")

        # Update last login
        try:
            """await db.execute_async(
                permission_query("UPDATE_USER_LAST_LOGIN"),
                {
                    "last_login": datetime.utcnow(),
                    "user_id": user["id"]
                }
            )"""
        except Exception:
            logger.exception("Failed to update last login")

        jwt_manager = get_jwt_manager()

        refresh_token, refresh_jti = await jwt_manager.create_refresh_token(
            user_data=user, request=request
        )

        access_token, _ = await jwt_manager.create_access_token(
            user_data=user, request=request, refresh_jti=refresh_jti
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=jwt_manager.refresh_token_ttl,
            path="/auth-api/refresh",
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=jwt_manager.access_token_ttl,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Login error")
        raise HTTPException(500, "Authentication failed")


# --------------------------
# REGISTER
# --------------------------
@router.post("/register", response_model=ResponseMessage)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db = Depends(get_db),
    system: SystemEntities = Depends(get_system_entities)
):
    """
    Register a new user with full atomic transaction.
    Supports:
    - Firebase registration
    - Email/password registration
    - Optional organization creation or joining
    """

    try:
        # -------------------------------------------------
        # Extract identity (Firebase or Email/Password)
        # -------------------------------------------------
        uid = None
        email = None
        display_name = None
        email_verified = False

        if user_data.firebase_token:
            auth_manager = get_auth_manager()
            firebase_user = auth_manager.verify_token(user_data.firebase_token)

            uid = firebase_user.provider_id
            email = firebase_user.email
            display_name = user_data.display_name or firebase_user.display_name
            email_verified = firebase_user.email_verified

            if user_data.email and user_data.email != email:
                raise HTTPException(400, "Email mismatch with Firebase token")

        else:
            if not user_data.uid:
                raise HTTPException(400, "UID is required for email/password registration")

            uid = user_data.uid
            email = user_data.email
            display_name = user_data.display_name
            email_verified = user_data.email_verified

        # -------------------------------------------------
        # Duplicate checks
        # -------------------------------------------------
        existing_user = await db.fetch_one_async(
            permission_query("GET_USER_BY_UID"),
            {"uid": uid}
        )
        if existing_user:
            raise HTTPException(400, "User already registered")

        existing_email = await db.fetch_one_async(
            permission_query("GET_USER_BY_EMAIL"),
            {"email": email}
        )
        if existing_email:
            raise HTTPException(400, "Email already registered")

        # -------------------------------------------------
        # Build user payload
        # -------------------------------------------------
        
        user_payload = {
            "uid": uid,
            "email": email,
            "display_name": display_name,
            "email_verified": email_verified,
            "department": None,
            "location": None,
            "status": "AC",
            "status_effective_from": datetime.utcnow().isoformat(),
            "roles": None,  # default role
        }

        # -------------------------------------------------
        # Build organization payload (optional)
        # -------------------------------------------------
        org_payload = None
        if user_data.organization_data:
            org_payload = {
                "type": user_data.organization_data.type,
                "id": user_data.organization_data.id,
                "name": user_data.organization_data.name,
            }

        # -------------------------------------------------
        # Initialize services
        # -------------------------------------------------
        org_service = OrganizationService(db, system)
        user_service = UserService(db, system)

        # -------------------------------------------------
        # FULL ATOMIC TRANSACTION
        # -------------------------------------------------
        async with db.transaction_async():
            org_id = None

            # 1. Create or validate organization
            if org_payload:
                if org_payload["type"] == "create":
                    user_payload["roles"] = [str(system.admin_role),str(system.system_role)]
                    org_id = await org_service.create_organization(
                        name=org_payload["name"],
                        created_by=system.system_user  # system user,
                    )
                elif org_payload["type"] == "join":
                    user_payload["roles"] = [str(system.system_role)]
                    exists = await org_service.get_organization_async(
                        org_payload["id"], mode="bool"
                    )
                    if not exists:
                        raise HTTPException(400, "Family does not exist")
                    org_id = org_payload["id"]

            # 2. Create user
            result = await user_service.bulk_create_users(
                org_id=org_id,
                users_data=[user_payload],
                created_by=system.system_user,
                org_action = org_payload["type"] if org_payload else "join",
            )

            if not result or result.get("count", 0) == 0:
                raise HTTPException(400, "User creation failed")

        # -------------------------------------------------
        # Success
        # -------------------------------------------------
        return ResponseMessage(
            message="User registered successfully",
            Success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Registration error: {e}")
        raise HTTPException(500, "Registration failed. Please try again.")


# --------------------------
# REFRESH TOKEN
# --------------------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db = Depends(get_db)
):
    try:
        jwt_manager = get_jwt_manager()

        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(401, "Refresh token not found")

        try:
            payload = await jwt_manager.verify_token(
                refresh_token, request, token_type="refresh"
            )
        except Exception:
            raise HTTPException(401, "Invalid refresh token")

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(401, "Invalid token payload")

        user = await db.fetch_one_async(
            permission_query("GET_USER_BY_ID"),
            {"user_id": user_id}
        )
        if not user:
            raise HTTPException(404, "User not found")

        access_token, _ = await jwt_manager.create_access_token(
            user_data=user, request=request, refresh_jti=payload.get("jti")
        )
        new_refresh_token, _ = await jwt_manager.create_refresh_token(
            user_data=user, request=request
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=jwt_manager.refresh_token_ttl,
            path="/auth-api/refresh"
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=jwt_manager.access_token_ttl
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Token refresh error: {e}")
        raise HTTPException(500, "Token refresh failed")


# --------------------------
# LOGOUT
# --------------------------
@router.post("/logout", response_model=SuccessResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        jwt_manager = get_jwt_manager()

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

            try:
                payload = await jwt_manager.verify_token(
                    token, request, token_type="access"
                )
            except Exception:
                logger.info("Logout with invalid/expired token")
            else:
                token_user_id = str(payload.get("user_id"))
                if token_user_id == str(current_user.id):
                    # Blacklist access token
                    await jwt_manager.blacklist_token(
                        payload.get("jti"),
                        current_user.id,
                        jwt_manager.access_token_ttl,
                    )

                    # Blacklist refresh token
                    refresh_jti = payload.get("refresh_jti")
                    if refresh_jti:
                        await jwt_manager.blacklist_token(
                            refresh_jti,
                            current_user.id,
                            jwt_manager.refresh_token_ttl,
                        )

        response.delete_cookie("refresh_token", path="/auth-api/refresh")

        return SuccessResponse(success=True, message="Logged out successfully")

    except Exception:
        logger.exception("Logout error")
        raise HTTPException(500, "Logout failed")


# --------------------------
# CURRENT USER
# --------------------------

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: AuthUser = Depends(get_current_user)
):
    return user


# --------------------------
# UPDATE USER
# --------------------------
@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    user_update: UserUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        display_name = user_update.display_name or current_user.display_name
        role = user_update.role or current_user.role
        email_verified = (
            user_update.email_verified
            if user_update.email_verified is not None
            else current_user.email_verified
        )

        success = await db.execute_async(
            permission_query("UPDATE_USER"),
            {
                "display_name": display_name,
                "role": role.value if hasattr(role, "value") else role,
                "email_verified": email_verified,
                "user_id": current_user.id,
            }
        )

        if not success:
            raise HTTPException(404, "User not found")

        updated_user = await db.fetch_one_async(
            permission_query("GET_USER_BY_ID"),
            {"user_id": current_user.id}
        )

        return UserResponse(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"User update error: {e}")
        raise HTTPException(500, "User update failed")


# --------------------------
# DELETE USER
# --------------------------
@router.delete("/me")
async def delete_current_user(
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        auth_manager = get_auth_manager()

        try:
            auth_manager.delete_user(current_user.uid)
        except Exception as e:
            logger.warning(f"Could not delete user from auth provider: {e}")

        success = await db.execute_async(
            permission_query("DELETE_USER"),
            {"user_id": current_user.id}
        )

        if not success:
            raise HTTPException(404, "User not found")

        return SuccessResponse(success=True, message="User account deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"User deletion error: {e}")
        raise HTTPException(500, "User deletion failed")


# --------------------------
# HEALTH CHECK
# --------------------------
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "authentication"
    }

# routers/auth.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, EmailStr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from utils.auth.jwt_utils import get_jwt_manager
from utils.database import get_db
from utils.auth.firebase_utils import firebase_manager
from utils.auth.jwt_utils import jwt_manager
from  utils.auth.auth_middleware import get_current_user
from models.auth_models import (
    LoginRequest, TokenResponse, UserCreate, UserResponse, 
    SuccessResponse, ErrorResponse, UserRole, AuthUser
)
from utils.database.query_manager import permission_query
import logging

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=lambda r: r.client.host)

router = APIRouter(prefix="/auth-api", tags=["authentication"])


# Exception handler for rate limiting
"""
@router.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "Too many requests. Please try again later.",
            "error": {"code": "rate_limit_exceeded", "details": f"Retry after {exc.retry_after} seconds"}
        }
    )
"""
# Request models with validation
class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    email_verified: Optional[bool] = None
    
    class Config:
        use_enum_values = True

# --------------------------
# Authentication Endpoints
# --------------------------
# routers/auth.py


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db=Depends(get_db),
):
    """Login with Firebase token"""
    try:
        firebase_user = firebase_manager.verify_firebase_token(
            login_data.firebase_token
        )
        user = await db.fetch_one(
            permission_query("GET_USER_BY_UID"), (firebase_user["uid"],)
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not registered",
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
            )

        # Update last login (not critical for auth invariants)
        try:
            await db.execute_update(
                permission_query("UPDATE_USER_LAST_LOGIN"),
                (datetime.utcnow(), user["id"]),
            )
        except Exception:
            logger.exception("Failed to update last login")

        jwt_manager = get_jwt_manager()

        # Create refresh token first (enforces stateful invariant)
        refresh_token, refresh_jti = await jwt_manager.create_refresh_token(
            user_data=user,
            request=request,
        )

        # Create access token bound to that refresh_jti
        access_token, _access_jti = await jwt_manager.create_access_token(
            user_data=user,
            request=request,
            refresh_jti=refresh_jti,
        )

        # Set refresh token cookie
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )

@router.post("/register", response_model=UserResponse)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db = Depends(get_db)
):
    """Register a new user (explicit registration required)"""
    try:
        # Check if user already exists
        existing_user = await db.fetch_one(
            permission_query("GET_USER_BY_UID"),
            (user_data.uid,)
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already registered"
            )
        
        # Check if email already exists
        existing_email = await db.fetch_one(
            permission_query("GET_USER_BY_EMAIL"),
            (user_data.email,)
        )
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user_id = db.execute_insert(
            permission_query("CREATE_USER"),
            (
                user_data.uid,
                user_data.email,
                user_data.display_name,
                user_data.role.value,
                user_data.email_verified,
                datetime.utcnow()  # created_at
            )
        )
        
        # Get created user
        user = await db.fetch_one(
            permission_query("GET_USER_BY_ID"),
            (user_id,)
        )
        
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db = Depends(get_db)
):
    """Refresh access token using refresh token from cookie"""
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )
        
        # Verify refresh token
        try:
            payload = jwt_manager.verify_token(refresh_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if user still exists
        user = await db.fetch_one(
            permission_query("GET_USER_BY_ID"),
            (user_id,)
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create new access token
        access_token = jwt_manager.create_access_token({"user_id": user_id})
        
        # Optionally create new refresh token (token rotation)
        new_refresh_token = jwt_manager.create_refresh_token({"user_id": user_id})
        
        # Set new refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=7*24*60*60,
            path="/auth-api/refresh"
        )
        
        return TokenResponse(
            access_token=access_token,
            expires_in=15*60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )



@router.post("/logout", response_model=SuccessResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: AuthUser = Depends(get_current_user),  # 
):
    """Logout current session/device (not global logout)"""
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

            jwt_manager = get_jwt_manager()
            try:
                payload = await jwt_manager.verify_token(
                    token, request, token_type="access"
                )
            except HTTPException as e:
                # Token invalid/expired – still clear cookie, but log for observability
                logger.info(
                    "Logout called with invalid/expired token for user %s: %s",
                    getattr(current_user, "id", None),
                    e.detail,
                )
            except Exception:
                logger.exception("Unexpected error during logout token verification")
            else:
                # Only blacklist if token belongs to the current user
                token_user_id = str(payload.get("user_id"))
                current_user_id = str(current_user.id)
                if token_user_id != current_user_id:
                    logger.warning(
                        "Logout attempted with token/user mismatch: token_user_id=%s, current_user_id=%s",
                        token_user_id,
                        current_user_id,
                    )
                else:
                    await jwt_manager.blacklist_token(
                        payload.get("jti"),
                        current_user_id,
                        jwt_manager.access_token_ttl,
                    )

                    refresh_jti = payload.get("refresh_jti")
                    if refresh_jti:
                        await jwt_manager.blacklist_token(
                            refresh_jti,
                            current_user_id,
                            jwt_manager.refresh_token_ttl,
                        )

        # Clear refresh cookie regardless of token validity
        response.delete_cookie(key="refresh_token", path="/auth-api/refresh")

        return SuccessResponse(success=True, message="Logged out successfully")

    except Exception:
        logger.exception("Logout error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )



@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: AuthUser = Depends(get_current_user)
):
    """Get current user information"""
    return user

@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    user_update: UserUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update current user information"""
    try:
        # Prepare update values
        display_name = user_update.display_name or current_user.display_name
        role = user_update.role or current_user.role
        email_verified = user_update.email_verified if user_update.email_verified is not None else current_user.email_verified
        
        # Update user in database
        success = db.execute_update(
            permission_query("UPDATE_USER"),
            (
                display_name,
                role.value if hasattr(role, 'value') else role,
                email_verified,
                current_user.id
            )
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get updated user
        updated_user = await db.fetch_one(
            permission_query("GET_USER_BY_ID"),
            (current_user.id,)
        )
        
        return UserResponse(**updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"User update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )

@router.delete("/me")
async def delete_current_user(
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete current user account"""
    try:
        success = db.execute_update(
            permission_query("DELETE_USER"),
            (current_user.id,)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return SuccessResponse(success=True, message="User account deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"User deletion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deletion failed"
        )

# --------------------------
# Health Check Endpoint
# --------------------------

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "authentication"
    }
from fastapi import APIRouter, Depends, HTTPException, status, Response
from utils.database import get_db
from utils.auth.firebase_utils import firebase_manager
from utils.auth.jwt_utils import jwt_manager
from utils.auth.middleware import get_current_user
from models.auth_models import (
    LoginRequest, TokenResponse, UserCreate, UserResponse, 
    SuccessResponse, ErrorResponse
)
from utils.database.query_manager import permission_query



router = APIRouter(prefix="/auth-api", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    db = Depends(get_db)
):
    """Login with Firebase token and get JWT tokens"""
    try:
        # Verify Firebase token
        firebase_user = firebase_manager.verify_firebase_token(login_data.firebase_token)
        
        # Check if user exists in our database
        user = await db.fetch_one(
            permission_query("GET_USER_BY_UID"),  # Using permission_query convenience function
            (firebase_user["uid"],)
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not registered. Please register first."
            )
        
        # Create JWT tokens
        access_token = jwt_manager.create_access_token({"user_id": user["id"]})
        refresh_token = jwt_manager.create_refresh_token({"user_id": user["id"]})
        
        # Set refresh token as httpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=7*24*60*60  # 7 days
        )
        
        return TokenResponse(
            access_token=access_token,
            expires_in=15*60  # 15 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/register", response_model=UserResponse)
async def register(
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
                user_data.email_verified
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Implementation for token refresh
        # This would typically extract the refresh token from cookies
        # and create a new access token
        
        # Placeholder implementation
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Token refresh not implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing cookies"""
    response.delete_cookie("refresh_token")
    return SuccessResponse(success=True, message="Logged out successfully")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: UserResponse = Depends(get_current_user)
):
    """Get current user information"""
    return user

@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    user_update: dict,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update current user information"""
    try:
        # Update user in database
        success = db.execute_update(
            permission_query("UPDATE_USER"),
            (
                user_update.get('display_name', current_user.display_name),
                user_update.get('role', current_user.role).value,
                user_update.get('email_verified', current_user.email_verified),
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User update failed: {str(e)}"
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User deletion failed: {str(e)}"
        )
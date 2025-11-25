from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.utils.database import get_db
from backend.utils.auth.middleware import get_current_user
from backend.utils.auth.permissions import require_permission, CommonPermissions
from models.auth_models import UserResponse, UserUpdate, SuccessResponse, User
from queries.query_loader import load_query

router = APIRouter(prefix="/auth-api/users", tags=["users"])

@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_permission(CommonPermissions.USER_VIEW)),
    db = Depends(get_db)
):
    """Get all users (admin only)"""
    users = db.execute_query("SELECT * FROM users ORDER BY created_at DESC", fetch=True)
    return [UserResponse(**user) for user in users]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission(CommonPermissions.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user by ID"""
    user = db.execute_single(
        load_query("auth/get_user_by_id.sql"),
        (user_id,)
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_permission(CommonPermissions.USER_MANAGE)),
    db = Depends(get_db)
):
    """Update user information"""
    try:
        # Build update fields
        update_fields = {}
        if user_data.display_name is not None:
            update_fields['display_name'] = user_data.display_name
        if user_data.role is not None:
            update_fields['role'] = user_data.role.value
        if user_data.email_verified is not None:
            update_fields['email_verified'] = user_data.email_verified
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update user
        success = db.execute_update(
            load_query("auth/update_user.sql"),
            (
                update_fields.get('display_name'),
                update_fields.get('role'),
                update_fields.get('email_verified'),
                user_id
            )
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get updated user
        user = db.execute_single(
            load_query("auth/get_user_by_id.sql"),
            (user_id,)
        )
        
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission(CommonPermissions.USER_MANAGE)),
    db = Depends(get_db)
):
    """Delete user"""
    try:
        success = db.execute_update(
            load_query("auth/delete_user.sql"),
            (user_id,)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return SuccessResponse(
            success=True,
            message="User deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
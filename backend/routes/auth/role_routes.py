from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from backend.utils.database import get_db
from backend.utils.auth.middleware import get_current_user
from backend.utils.auth.permissions import require_permission_id, CommonPermissionIds
from models.auth_models import SuccessResponse, User
from queries.query_manager import auth_query

router = APIRouter(prefix="/auth-api/roles", tags=["roles"])

# USER-ROLE ASSIGNMENT ENDPOINTS
@router.get("/user/{user_id}")
async def get_user_roles(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get roles assigned to a user"""
    user_data = db.execute_single(
        auth_query("GET_USER_BY_ID"),
        (user_id,)
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "roles": [user_data["role"]],  # Single role for now, can be extended to multiple
            "primary_role": user_data["role"]
        }
    }

@router.put("/user/{user_id}")
async def update_user_role(
    user_id: int,
    role_data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Update user's primary role"""
    new_role = role_data.get("role")
    
    if new_role not in ["basic", "creator", "moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be one of: basic, creator, moderator, admin"
        )
    
    # Get current user data
    user_data = db.execute_single(
        auth_query("GET_USER_BY_ID"),
        (user_id,)
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = user_data["role"]
    
    # Update user role
    success = db.execute_update(
        auth_query("UPDATE_USER"),
        (user_data["display_name"], new_role, user_data["email_verified"], user_id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )
    
    # Log the role change
    db.execute_insert(
        auth_query("LOG_PERMISSION_ACTION"),
        (user_id, 0, f'ROLE_CHANGE:{old_role}->{new_role}', current_user.id)
    )
    
    return SuccessResponse(
        success=True,
        message=f"User role updated from {old_role} to {new_role}"
    )

@router.get("/users/with-role/{role_name}")
async def get_users_with_role(
    role_name: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get all users with a specific role"""
    if role_name not in ["basic", "creator", "moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be one of: basic, creator, moderator, admin"
        )
    
    users = db.execute_query(
        "SELECT id, email, display_name, role, created_at FROM users WHERE role = %s ORDER BY created_at DESC",
        (role_name,),
        fetch=True
    )
    
    return {
        "success": True,
        "data": {
            "role": role_name,
            "users": users,
            "user_count": len(users)
        }
    }

@router.post("/users/bulk-update")
async def bulk_update_user_roles(
    update_data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Bulk update roles for multiple users"""
    user_updates = update_data.get("updates", [])
    updated = 0
    failed = 0
    
    for update in user_updates:
        user_id = update.get("user_id")
        new_role = update.get("role")
        
        if not user_id or new_role not in ["basic", "creator", "moderator", "admin"]:
            failed += 1
            continue
        
        try:
            # Get current user data
            user_data = db.execute_single(
                auth_query("GET_USER_BY_ID"),
                (user_id,)
            )
            
            if not user_data:
                failed += 1
                continue
            
            old_role = user_data["role"]
            
            # Update user role
            success = db.execute_update(
                auth_query("UPDATE_USER"),
                (user_data["display_name"], new_role, user_data["email_verified"], user_id)
            )
            
            if success:
                updated += 1
                # Log the role change
                db.execute_insert(
                    auth_query("LOG_PERMISSION_ACTION"),
                    (user_id, 0, f'ROLE_CHANGE:{old_role}->{new_role}', current_user.id)
                )
            else:
                failed += 1
                
        except Exception as e:
            print(f"Failed to update user {user_id}: {str(e)}")
            failed += 1
    
    return SuccessResponse(
        success=True,
        message=f"Bulk role update: {updated} updated, {failed} failed"
    )

@router.get("/stats")
async def get_role_statistics(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get statistics about role distribution"""
    stats = db.execute_query(
        "SELECT role, COUNT(*) as user_count FROM users GROUP BY role ORDER BY user_count DESC",
        fetch=True
    )
    
    total_users = sum(row["user_count"] for row in stats)
    
    role_distribution = []
    for row in stats:
        percentage = (row["user_count"] / total_users) * 100 if total_users > 0 else 0
        role_distribution.append({
            "role": row["role"],
            "user_count": row["user_count"],
            "percentage": round(percentage, 2)
        })
    
    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "role_distribution": role_distribution,
            "most_common_role": stats[0]["role"] if stats else None
        }
    }
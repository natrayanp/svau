from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime

from backend.utils.database import get_db
from backend.utils.auth.middleware import get_current_user
from backend.utils.auth.permissions import require_permission_id, CommonPermissionIds
from models.auth_models import SuccessResponse, User
from queries.query_manager import auth_query

router = APIRouter(prefix="/auth-api/roles", tags=["roles"])

# ============ CONSISTENT RESPONSE HELPERS ============
def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Consistent success response structure"""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return response

def error_response(message: str) -> Dict[str, Any]:
    """Consistent error response structure"""
    return {"success": False, "message": message}

# ============ USER-ROLE ASSIGNMENT ENDPOINTS ============
@router.get("/user/{user_id}")
async def get_user_roles(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get roles assigned to a user"""
    try:
        user_data = db.execute_single(
            auth_query("GET_USER_BY_ID"),
            (user_id,)
        )
        
        if not user_data:
            return error_response("User not found")
        
        response_data = {
            "user_id": user_id,
            "roles": [user_data["role"]],
            "primary_role": user_data["role"]
        }
        
        return success_response(response_data, "User roles loaded")
    except Exception as e:
        return error_response(f"Failed to get user roles: {str(e)}")

@router.put("/user/{user_id}")
async def update_user_role(
    user_id: int,
    role_data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Update user's primary role"""
    try:
        new_role = role_data.get("role")
        
        if new_role not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role. Must be one of: basic, creator, moderator, admin")
        
        # Get current user data
        user_data = db.execute_single(
            auth_query("GET_USER_BY_ID"),
            (user_id,)
        )
        
        if not user_data:
            return error_response("User not found")
        
        old_role = user_data["role"]
        
        # Update user role
        success = db.execute_update(
            auth_query("UPDATE_USER"),
            (user_data["display_name"], new_role, user_data["email_verified"], user_id)
        )
        
        if not success:
            return error_response("Failed to update user role")
        
        # Log the role change
        db.execute_insert(
            auth_query("LOG_PERMISSION_ACTION"),
            (user_id, 0, f'ROLE_CHANGE:{old_role}->{new_role}', current_user.id)
        )
        
        return success_response(message=f"User role updated from {old_role} to {new_role}")
    except Exception as e:
        return error_response(f"Failed to update user role: {str(e)}")

@router.get("/users/with-role/{role_name}")
async def get_users_with_role(
    role_name: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get all users with a specific role"""
    try:
        if role_name not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role. Must be one of: basic, creator, moderator, admin")
        
        users = db.execute_query(
            "SELECT id, email, display_name, role, created_at FROM users WHERE role = %s ORDER BY created_at DESC",
            (role_name,),
            fetch=True
        )
        
        response_data = {
            "role": role_name,
            "users": users,
            "user_count": len(users)
        }
        
        return success_response(response_data, f"Users with role {role_name} loaded")
    except Exception as e:
        return error_response(f"Failed to get users with role: {str(e)}")

@router.post("/users/bulk-update")
async def bulk_update_user_roles(
    update_data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Bulk update roles for multiple users"""
    try:
        user_updates = update_data.get("updates", [])
        updated = 0
        failed = 0
        results = []
        
        for update in user_updates:
            user_id = update.get("user_id")
            new_role = update.get("role")
            
            if not user_id or new_role not in ["basic", "creator", "moderator", "admin"]:
                results.append({
                    "user_id": user_id,
                    "success": False,
                    "message": "Invalid user ID or role"
                })
                failed += 1
                continue
            
            try:
                # Get current user data
                user_data = db.execute_single(
                    auth_query("GET_USER_BY_ID"),
                    (user_id,)
                )
                
                if not user_data:
                    results.append({
                        "user_id": user_id,
                        "success": False,
                        "message": "User not found"
                    })
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
                    results.append({
                        "user_id": user_id,
                        "success": True,
                        "message": f"Role updated from {old_role} to {new_role}"
                    })
                else:
                    failed += 1
                    results.append({
                        "user_id": user_id,
                        "success": False,
                        "message": "Failed to update role"
                    })
                    
            except Exception as e:
                failed += 1
                results.append({
                    "user_id": user_id,
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
        
        response_data = {
            "updated": updated,
            "failed": failed,
            "results": results
        }
        
        return success_response(
            response_data,
            f"Bulk role update: {updated} updated, {failed} failed"
        )
    except Exception as e:
        return error_response(f"Bulk update failed: {str(e)}")

@router.get("/stats")
async def get_role_statistics(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get statistics about role distribution"""
    try:
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
        
        response_data = {
            "total_users": total_users,
            "role_distribution": role_distribution,
            "most_common_role": stats[0]["role"] if stats else None,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return success_response(response_data, "Role statistics loaded")
    except Exception as e:
        return error_response(f"Failed to get role statistics: {str(e)}")

# ============ ADDITIONAL ROLE ASSIGNMENT ENDPOINTS ============
@router.post("/users/{user_id}/roles")
async def assign_user_to_role(
    user_id: int,
    role_data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Assign a user to a role (add to existing roles)"""
    try:
        new_role = role_data.get("role")
        
        if new_role not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role. Must be one of: basic, creator, moderator, admin")
        
        # Get current user data
        user_data = db.execute_single(
            auth_query("GET_USER_BY_ID"),
            (user_id,)
        )
        
        if not user_data:
            return error_response("User not found")
        
        old_role = user_data["role"]
        
        # Update user role
        success = db.execute_update(
            auth_query("UPDATE_USER"),
            (user_data["display_name"], new_role, user_data["email_verified"], user_id)
        )
        
        if not success:
            return error_response("Failed to assign role to user")
        
        # Log the role assignment
        db.execute_insert(
            auth_query("LOG_PERMISSION_ACTION"),
            (user_id, 0, f'ROLE_ASSIGN:{new_role}', current_user.id)
        )
        
        return success_response(message=f"User assigned to role: {new_role}")
    except Exception as e:
        return error_response(f"Failed to assign role: {str(e)}")

@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_user_from_role(
    user_id: int,
    role_name: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Remove a user from a role"""
    try:
        if role_name not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role name")
        
        # Get current user data
        user_data = db.execute_single(
            auth_query("GET_USER_BY_ID"),
            (user_id,)
        )
        
        if not user_data:
            return error_response("User not found")
        
        current_role = user_data["role"]
        
        if current_role != role_name:
            return error_response(f"User is not assigned to role: {role_name}")
        
        # Set user to basic role (default)
        success = db.execute_update(
            auth_query("UPDATE_USER"),
            (user_data["display_name"], "basic", user_data["email_verified"], user_id)
        )
        
        if not success:
            return error_response("Failed to remove user from role")
        
        # Log the role removal
        db.execute_insert(
            auth_query("LOG_PERMISSION_ACTION"),
            (user_id, 0, f'ROLE_REMOVE:{role_name}', current_user.id)
        )
        
        return success_response(message=f"User removed from role: {role_name}")
    except Exception as e:
        return error_response(f"Failed to remove user from role: {str(e)}")
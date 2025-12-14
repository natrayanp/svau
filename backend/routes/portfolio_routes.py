from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from utils.database import get_db
from  utils.auth.auth_middleware import get_current_user
from utils.auth.permissions import (
    require_permission_id, ExplicitPermissionSystem, 
    PERMISSION_STRUCTURE, CommonPermissionIds, RolePermissions,
    ROLE_TEMPLATES, require_minimum_power
)
from models.auth_models import (
    UserPermissionsRequest, UserPermissionsResponse, SuccessResponse,
    User, PermissionStructureAPIResponse, RolePermissionsResponse,
    PermissionValidationRequest, PermissionValidationResponse,
    AllowedPermissionsResponse, PowerAnalysisResponse, RoleTemplate
)
from queries.query_manager import auth_query

router = APIRouter(prefix="/auth-api/permissions", tags=["permissions"])

# PERMISSION STRUCTURE ENDPOINTS
@router.get("/structures", response_model=PermissionStructureAPIResponse)
async def get_permission_structure(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Get complete permission structure with power levels"""
    total_menus = sum(len(module["menus"]) for module in PERMISSION_STRUCTURE["modules"])
    total_cards = sum(len(menu["cards"]) for module in PERMISSION_STRUCTURE["modules"] for menu in module["menus"])
    total_permissions = sum(len(card["permissions"]) for module in PERMISSION_STRUCTURE["modules"] for menu in module["menus"] for card in menu["cards"])
    
    return PermissionStructureAPIResponse(
        success=True,
        data={
            "modules": PERMISSION_STRUCTURE["modules"],
            "metadata": {
                "total_modules": len(PERMISSION_STRUCTURE["modules"]),
                "total_menus": total_menus,
                "total_cards": total_cards,
                "total_permissions": total_permissions,
                "last_updated": datetime.utcnow().isoformat()
            }
        }
    )


# USER PERMISSION MANAGEMENT
@router.get("/user/{user_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user's permission IDs"""
    permissions = await db.fetch_one(
        auth_query("GET_USER_PERMISSION_IDS"),
        (user_id,),
        fetch=True
    )
    
    permission_ids = [row['permission_id'] for row in permissions]
    
    return UserPermissionsResponse(
        user_id=user_id,
        permission_ids=permission_ids
    )

@router.post("/user/{user_id}", response_model=SuccessResponse)
async def grant_permissions(
    user_id: int,
    permission_data: UserPermissionsRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Grant permissions to user by IDs"""
    perm_system = ExplicitPermissionSystem()
    granted = 0
    failed = 0
    
    for permission_id in permission_data.permission_ids:
        try:
            # Validate permission ID exists
            if not perm_system.get_permission_details(permission_id):
                failed += 1
                continue
                
            db.execute_insert(
                auth_query("ADD_USER_PERMISSION"),
                (user_id, permission_id, current_user.id)
            )
            granted += 1
            
            # Log the action
            db.execute_insert(
                auth_query("LOG_PERMISSION_ACTION"),
                (user_id, permission_id, 'GRANT', current_user.id)
            )
            
        except Exception as e:
            print(f"Failed to grant permission {permission_id}: {str(e)}")
            failed += 1
    
    # Clear cache
    perm_system.get_user_permission_ids.cache_clear()
    
    return SuccessResponse(
        success=True,
        message=f"Permissions updated: {granted} granted, {failed} failed"
    )

@router.delete("/user/{user_id}", response_model=SuccessResponse)
async def revoke_permissions(
    user_id: int,
    permission_data: UserPermissionsRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Revoke permissions from user by IDs"""
    perm_system = ExplicitPermissionSystem()
    revoked = 0
    failed = 0
    
    for permission_id in permission_data.permission_ids:
        try:
            success = db.execute_update(
                auth_query("REMOVE_USER_PERMISSION"),
                (user_id, permission_id)
            )
            
            if success:
                revoked += 1
                db.execute_insert(
                    auth_query("LOG_PERMISSION_ACTION"),
                    (user_id, permission_id, 'REVOKE', current_user.id)
                )
            else:
                failed += 1
            
        except Exception as e:
            print(f"Failed to revoke permission {permission_id}: {str(e)}")
            failed += 1
    
    perm_system.get_user_permission_ids.cache_clear()
    
    return SuccessResponse(
        success=True,
        message=f"Permissions revoked: {revoked} revoked, {failed} failed"
    )

@router.get("/user/{user_id}/effective", response_model=UserPermissionsResponse)
async def get_effective_permissions(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user's effective permissions (including role-based)"""
    perm_system = ExplicitPermissionSystem()
    effective_permissions = perm_system.get_user_permission_ids_with_roles(user_id, db)
    
    return UserPermissionsResponse(
        user_id=user_id,
        permission_ids=list(effective_permissions)
    )

# ROLE MANAGEMENT ENDPOINTS
@router.get("/roles/{role_name}", response_model=RolePermissionsResponse)
async def get_role_permissions(role_name: str):
    """Get permissions assigned to a specific role"""
    role_permission_ids = RolePermissions.get_permission_ids_for_role(role_name)
    
    return RolePermissionsResponse(
        role=role_name,
        permission_ids=list(role_permission_ids),
        permission_count=len(role_permission_ids)
    )



# PERMISSION CHECKING
@router.post("/check/{permission_id}", response_model=SuccessResponse)
async def check_permission(
    permission_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check if current user has a specific permission by ID"""
    perm_system = ExplicitPermissionSystem()
    user_permission_ids = perm_system.get_user_permission_ids_with_roles(current_user.id, db)
    
    if perm_system.check_permission_by_id(user_permission_ids, permission_id):
        return SuccessResponse(success=True, message="Permission granted")
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

@router.get("/user/{user_id}/details")
async def get_user_permissions_with_details(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user permissions with detailed information"""
    permissions = await db.fetch_one(
        auth_query("GET_USER_PERMISSIONS_WITH_DETAILS"),
        (user_id,),
        fetch=True
    )
    
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "permissions": permissions
        }
    }
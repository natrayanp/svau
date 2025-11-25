from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from backend.utils.database import get_db
from backend.utils.auth.middleware import get_current_user
from backend.utils.auth.permissions import (
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
@router.get("/structure", response_model=PermissionStructureAPIResponse)
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

# POWER-BASED PERMISSION VALIDATION ENDPOINTS
@router.post("/validate-child-permissions", response_model=PermissionValidationResponse)
async def validate_child_permissions(
    validation_data: PermissionValidationRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Validate if child permissions are allowed by parent constraints"""
    perm_system = ExplicitPermissionSystem()
    
    result = perm_system.validate_child_permissions(
        validation_data.parent_permission_ids,
        validation_data.child_permission_ids
    )
    
    return PermissionValidationResponse(**result)

@router.get("/allowed-child-permissions", response_model=AllowedPermissionsResponse)
async def get_allowed_child_permissions(
    parent_permission_ids: str,  # Comma-separated list of IDs
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Get permissions that children can have based on parent's max power"""
    perm_system = ExplicitPermissionSystem()
    
    # Parse comma-separated IDs
    parent_ids = [int(id.strip()) for id in parent_permission_ids.split(",") if id.strip()]
    
    allowed_permissions = perm_system.get_allowed_child_permissions(parent_ids)
    max_parent_power = perm_system.get_max_power_from_permissions(parent_ids)
    
    return AllowedPermissionsResponse(
        allowed_permissions=allowed_permissions,
        max_parent_power=max_parent_power
    )

@router.get("/default-permissions/new-module")
async def get_default_permissions_for_new_module(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Get default permissions for a new module (least powerful)"""
    perm_system = ExplicitPermissionSystem()
    default_permissions = perm_system.get_default_permissions_for_new_module()
    
    return {
        "success": True,
        "data": {
            "default_permission_ids": default_permissions,
            "default_permissions": [perm_system.get_permission_details(pid) for pid in default_permissions]
        }
    }

@router.post("/permissions/follow-parent")
async def get_permissions_following_parent(
    data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Get permissions that follow parent's permissions within constraints"""
    perm_system = ExplicitPermissionSystem()
    
    parent_permission_ids = data.get("parent_permission_ids", [])
    available_permission_ids = data.get("available_permission_ids", [])
    
    following_permissions = perm_system.get_permissions_following_parent(
        parent_permission_ids, available_permission_ids
    )
    
    return {
        "success": True,
        "data": {
            "following_permission_ids": following_permissions,
            "following_permissions": [perm_system.get_permission_details(pid) for pid in following_permissions]
        }
    }

# USER PERMISSION MANAGEMENT
@router.get("/user/{user_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user's permission IDs"""
    permissions = db.execute_query(
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

@router.get("/user/{user_id}/power-analysis")
async def get_user_power_analysis(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get power analysis for a user"""
    perm_system = ExplicitPermissionSystem()
    user_permission_ids = perm_system.get_user_permission_ids_with_roles(user_id, db)
    
    permission_details = []
    total_power = 0
    max_power = 0
    
    for perm_id in user_permission_ids:
        perm_details = perm_system.get_permission_details(perm_id)
        if perm_details:
            permission_details.append(perm_details)
            total_power += perm_details["power_level"]
            max_power = max(max_power, perm_details["power_level"])
    
    avg_power = total_power / len(permission_details) if permission_details else 0
    
    # Power distribution
    power_distribution = {
        "low": len([p for p in permission_details if p["power_level"] <= 30]),
        "medium": len([p for p in permission_details if 31 <= p["power_level"] <= 60]),
        "high": len([p for p in permission_details if 61 <= p["power_level"] <= 80]),
        "critical": len([p for p in permission_details if p["power_level"] > 80])
    }
    
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "permission_count": len(permission_details),
            "max_power": max_power,
            "average_power": round(avg_power, 2),
            "power_distribution": power_distribution,
            "most_powerful_permissions": [
                p for p in permission_details if p["power_level"] == max_power
            ]
        }
    }

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

@router.get("/roles/{role_name}/power-analysis", response_model=PowerAnalysisResponse)
async def get_role_power_analysis(role_name: str):
    """Get power analysis for a role"""
    analysis = RolePermissions.get_role_power_analysis(role_name)
    return PowerAnalysisResponse(**analysis)

@router.get("/roles")
async def get_all_roles():
    """Get all available roles with their power analysis"""
    roles = ["basic", "creator", "moderator", "admin"]
    role_data = []
    
    for role in roles:
        analysis = RolePermissions.get_role_power_analysis(role)
        role_data.append(analysis)
    
    return {
        "success": True,
        "data": role_data
    }

@router.get("/roles/conflicts")
async def get_role_conflicts():
    """Get permission conflicts between roles"""
    role_permissions = {
        "basic": RolePermissions.get_permission_ids_for_role("basic"),
        "creator": RolePermissions.get_permission_ids_for_role("creator"),
        "moderator": RolePermissions.get_permission_ids_for_role("moderator"),
        "admin": RolePermissions.get_permission_ids_for_role("admin")
    }
    
    conflicts = RolePermissions.find_permission_conflicts(role_permissions)
    
    return {
        "success": True,
        "data": {
            "conflicts": conflicts,
            "total_conflicts": len(conflicts)
        }
    }

# ROLE TEMPLATES ENDPOINTS
@router.get("/templates")
async def get_role_templates():
    """Get all available role templates"""
    return {
        "success": True,
        "data": ROLE_TEMPLATES
    }

@router.get("/templates/{template_name}")
async def get_role_template(template_name: str):
    """Get a specific role template"""
    template = ROLE_TEMPLATES.get(template_name)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    return {
        "success": True,
        "data": template
    }

@router.post("/templates")
async def create_role_template(
    template_data: RoleTemplate,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Create a new role template"""
    template_key = template_data.name.lower().replace(" ", "_")
    
    if template_key in ROLE_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{template_key}' already exists"
        )
    
    ROLE_TEMPLATES[template_key] = {
        "name": template_data.name,
        "description": template_data.description,
        "permission_ids": template_data.permission_ids,
        "power_level": template_data.power_level
    }
    
    return SuccessResponse(
        success=True,
        message=f"Template '{template_data.name}' created successfully"
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

@router.post("/check-power/{required_power}", response_model=SuccessResponse)
async def check_power_level(
    required_power: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check if current user has sufficient power level"""
    perm_system = ExplicitPermissionSystem()
    
    if perm_system.can_user_access_power_level(current_user.id, required_power, db):
        return SuccessResponse(success=True, message=f"Power level {required_power} granted")
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient power level. Required: {required_power}"
        )

@router.get("/user/{user_id}/details")
async def get_user_permissions_with_details(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user permissions with detailed information"""
    permissions = db.execute_query(
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
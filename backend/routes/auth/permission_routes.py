from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.utils.database import get_db
from backend.utils.auth.middleware import get_current_user
from backend.utils.auth.permissions import (
    require_permission_id, ExplicitPermissionSystem, 
    CommonPermissionIds, RolePermissions, ROLE_TEMPLATES
)
from models.auth_models import (
    UserPermissionsRequest, UserPermissionsResponse, SuccessResponse,
    User, PermissionStructureAPIResponse, RolePermissionsResponse,
    RolePermissionsUpdateRequest, PermissionValidationRequest,
    PermissionValidationResponse, AllowedPermissionsResponse,
    PowerAnalysisResponse, RoleTemplate
)
from queries.query_manager import auth_query

router = APIRouter(prefix="/auth-api/permissions", tags=["permissions"])

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

# ============ PERMISSION STRUCTURE ENDPOINTS ============
@router.get("/structure")
async def get_permission_structure(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Get complete permission structure from database - returns string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        structure = perm_system.get_permission_structure(db)
        
        return success_response(structure, "Permission structure loaded successfully")
    except Exception as e:
        return error_response(f"Failed to load permission structure: {str(e)}")

# ============ ROLE PERMISSION MANAGEMENT ============
@router.get("/roles/{role_name}")
async def get_role_permissions(
    role_name: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get permissions assigned to a specific role - returns string IDs"""
    try:
        if role_name not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role name")
        
        perm_system = ExplicitPermissionSystem()
        role_permission_ids = perm_system.db_system.get_role_permissions_from_db(role_name, db)
        
        response_data = RolePermissionsResponse(
            role=role_name,
            permission_ids=list(role_permission_ids),  # Already string IDs
            permission_count=len(role_permission_ids)
        )
        
        return success_response(response_data.dict(), f"Role permissions for {role_name} loaded")
    except Exception as e:
        return error_response(f"Failed to get role permissions: {str(e)}")

@router.put("/roles/{role_name}/permissions")
async def update_role_permissions(
    role_name: str,
    permission_data: RolePermissionsUpdateRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Update permissions for a specific role - accepts string IDs"""
    try:
        if role_name not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role name")
        
        perm_system = ExplicitPermissionSystem()
        
        # Validate permission IDs exist (accepts string IDs)
        invalid_permissions = []
        for perm_id in permission_data.permission_ids:
            if not perm_system.validate_permission_id(perm_id, db):
                invalid_permissions.append(perm_id)
        
        if invalid_permissions:
            return error_response(f"Invalid permission IDs: {invalid_permissions}")
        
        # Save to database (handles string to int conversion internally)
        success = perm_system.save_role_permissions(
            role_name, 
            permission_data.permission_ids,  # String IDs
            current_user.id, 
            db
        )
        
        if not success:
            return error_response("Failed to save role permissions")
        
        # Log the bulk permission update
        db.execute_insert(
            auth_query("LOG_PERMISSION_ACTION"),
            (0, 0, f'ROLE_PERMISSIONS_UPDATE:{role_name}', current_user.id)
        )
        
        return success_response(message=f"Role permissions updated successfully for {role_name}")
        
    except Exception as e:
        return error_response(f"Failed to update role permissions: {str(e)}")

# ============ POWER ANALYSIS ENDPOINTS ============
@router.get("/roles/{role_name}/analysis")
async def get_role_power_analysis(
    role_name: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get power analysis for a role from database - uses string IDs"""
    try:
        if role_name not in ["basic", "creator", "moderator", "admin"]:
            return error_response("Invalid role name")
        
        perm_system = ExplicitPermissionSystem()
        role_permissions = perm_system.db_system.get_role_permissions_from_db(role_name, db)  # String IDs
        
        permission_details = []
        total_power = 0
        max_power = 0
        
        for perm_id in role_permissions:
            perm_details = perm_system.db_system.get_permission_details(perm_id, db)  # String ID
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
        
        analysis_data = {
            "role": role_name,
            "permission_count": len(permission_details),
            "max_power": max_power,
            "average_power": round(avg_power, 2),
            "power_distribution": power_distribution,
            "most_powerful_permissions": [
                p for p in permission_details if p["power_level"] == max_power
            ],
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        return success_response(analysis_data, f"Power analysis for {role_name} completed")
    except Exception as e:
        return error_response(f"Failed to analyze role permissions: {str(e)}")

@router.get("/user/{user_id}/power-analysis")
async def get_user_power_analysis(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get power analysis for a user - uses string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        user_permission_ids = perm_system.get_user_permission_ids_with_roles(user_id, db)  # String IDs
        
        permission_details = []
        total_power = 0
        max_power = 0
        
        for perm_id in user_permission_ids:
            perm_details = perm_system.get_permission_details(perm_id, db)  # String ID
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
        
        analysis_data = {
            "user_id": user_id,
            "permission_count": len(permission_details),
            "max_power": max_power,
            "average_power": round(avg_power, 2),
            "power_distribution": power_distribution,
            "most_powerful_permissions": [
                p for p in permission_details if p["power_level"] == max_power
            ],
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        return success_response(analysis_data, f"Power analysis for user {user_id} completed")
    except Exception as e:
        return error_response(f"Failed to analyze user permissions: {str(e)}")

# ============ USER PERMISSION MANAGEMENT ============
@router.get("/user/{user_id}")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user's permission IDs - returns string IDs"""
    try:
        permissions = db.execute_query(
            auth_query("GET_USER_PERMISSION_IDS"),
            (user_id,),
            fetch=True
        )
        
        # Convert to string IDs for frontend
        permission_ids = [str(row['permission_id']) for row in permissions]
        response_data = UserPermissionsResponse(
            user_id=user_id,  # Keep internal ID as int
            permission_ids=permission_ids  # String IDs for frontend
        )
        
        return success_response(response_data.dict(), f"User permissions loaded for user {user_id}")
    except Exception as e:
        return error_response(f"Failed to get user permissions: {str(e)}")

@router.post("/user/{user_id}")
async def grant_permissions(
    user_id: int,
    permission_data: UserPermissionsRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Grant permissions to user by IDs - accepts string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        granted = 0
        failed = 0
        results = []
        
        for permission_id in permission_data.permission_ids:
            try:
                # Validate permission ID exists (accepts string)
                if not perm_system.validate_permission_id(permission_id, db):
                    results.append({
                        "permission_id": permission_id,
                        "success": False,
                        "message": "Invalid permission ID"
                    })
                    failed += 1
                    continue
                
                # Convert to int for database
                permission_id_int = int(permission_id)
                    
                db.execute_insert(
                    auth_query("ADD_USER_PERMISSION"),
                    (user_id, permission_id_int, current_user.id)
                )
                granted += 1
                results.append({
                    "permission_id": permission_id,
                    "success": True,
                    "message": "Permission granted"
                })
                
                # Log the action
                db.execute_insert(
                    auth_query("LOG_PERMISSION_ACTION"),
                    (user_id, permission_id_int, 'GRANT', current_user.id)
                )
                
            except Exception as e:
                failed += 1
                results.append({
                    "permission_id": permission_id,
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
        
        # Clear cache
        perm_system.get_user_permission_ids.cache_clear()
        
        return success_response(
            {"results": results},
            f"Permissions updated: {granted} granted, {failed} failed"
        )
    except Exception as e:
        return error_response(f"Failed to grant permissions: {str(e)}")

@router.delete("/user/{user_id}")
async def revoke_permissions(
    user_id: int,
    permission_data: UserPermissionsRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_MANAGE)),
    db = Depends(get_db)
):
    """Revoke permissions from user by IDs - accepts string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        revoked = 0
        failed = 0
        results = []
        
        for permission_id in permission_data.permission_ids:
            try:
                # Convert to int for database
                permission_id_int = int(permission_id)
                
                success = db.execute_update(
                    auth_query("REMOVE_USER_PERMISSION"),
                    (user_id, permission_id_int)
                )
                
                if success:
                    revoked += 1
                    results.append({
                        "permission_id": permission_id,
                        "success": True,
                        "message": "Permission revoked"
                    })
                    db.execute_insert(
                        auth_query("LOG_PERMISSION_ACTION"),
                        (user_id, permission_id_int, 'REVOKE', current_user.id)
                    )
                else:
                    failed += 1
                    results.append({
                        "permission_id": permission_id,
                        "success": False,
                        "message": "Permission not found"
                    })
                
            except Exception as e:
                failed += 1
                results.append({
                    "permission_id": permission_id,
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
        
        perm_system.get_user_permission_ids.cache_clear()
        
        return success_response(
            {"results": results},
            f"Permissions revoked: {revoked} revoked, {failed} failed"
        )
    except Exception as e:
        return error_response(f"Failed to revoke permissions: {str(e)}")

@router.get("/user/{user_id}/effective")
async def get_effective_permissions(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user's effective permissions (including role-based) - returns string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        effective_permissions = perm_system.get_user_permission_ids_with_roles(user_id, db)  # String IDs
        
        response_data = UserPermissionsResponse(
            user_id=user_id,
            permission_ids=list(effective_permissions)  # String IDs
        )
        
        return success_response(response_data.dict(), "Effective permissions loaded")
    except Exception as e:
        return error_response(f"Failed to get effective permissions: {str(e)}")

# ============ PERMISSION VALIDATION ============
@router.post("/validate-child-permissions")
async def validate_child_permissions(
    validation_data: PermissionValidationRequest,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Validate if child permissions are allowed by parent constraints - accepts string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        
        result = perm_system.validate_child_permissions(
            validation_data.parent_permission_ids,  # String IDs
            validation_data.child_permission_ids,   # String IDs
            db
        )
        
        return success_response(result, "Permission validation completed")
    except Exception as e:
        return error_response(f"Failed to validate permissions: {str(e)}")

@router.get("/allowed-child-permissions")
async def get_allowed_child_permissions(
    parent_permission_ids: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Get permissions that children can have based on parent's max power - accepts string IDs"""
    try:
        # Parse comma-separated string IDs
        parent_ids = [id.strip() for id in parent_permission_ids.split(",") if id.strip()]
        
        if not parent_ids:
            return error_response("No parent permission IDs provided")
        
        perm_system = ExplicitPermissionSystem()
        allowed_permissions = perm_system.get_allowed_child_permissions(parent_ids, db)  # String IDs
        max_parent_power = perm_system.get_max_power_from_permissions(parent_ids, db)
        
        response_data = AllowedPermissionsResponse(
            allowed_permissions=allowed_permissions,
            max_parent_power=max_parent_power
        )
        
        return success_response(response_data.dict(), "Allowed child permissions retrieved")
    except ValueError:
        return error_response("Invalid permission ID format")
    except Exception as e:
        return error_response(f"Failed to get allowed permissions: {str(e)}")

# ============ PERMISSION CHECKING ============
@router.post("/check/{permission_id}")
async def check_permission(
    permission_id: int,  # Backend uses int for permission dependencies
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check if current user has a specific permission by ID - backend uses int"""
    try:
        perm_system = ExplicitPermissionSystem()
        user_permission_ids = perm_system.get_user_permission_ids_with_roles(current_user.id, db)  # String IDs
        
        # Convert permission_id to string for comparison
        permission_id_str = str(permission_id)
        
        if perm_system.check_permission_by_id(user_permission_ids, permission_id_str):
            return success_response(message="Permission granted")
        else:
            return error_response("Permission denied")
    except Exception as e:
        return error_response(f"Failed to check permission: {str(e)}")

@router.post("/check-power/{required_power}")
async def check_power_level(
    required_power: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check if current user has sufficient power level"""
    try:
        if required_power < 0 or required_power > 100:
            return error_response("Power level must be between 0 and 100")
        
        perm_system = ExplicitPermissionSystem()
        
        if perm_system.can_user_access_power_level(current_user.id, required_power, db):
            return success_response(message=f"Power level {required_power} granted")
        else:
            user_max_power = perm_system.get_user_max_power(current_user.id, db)
            return error_response(f"Insufficient power level. Required: {required_power}, Your max: {user_max_power}")
    except Exception as e:
        return error_response(f"Failed to check power level: {str(e)}")

# ============ SYSTEM ROLES OVERVIEW ============
@router.get("/roles")
async def get_all_roles(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get all available roles with their permission counts - returns string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        
        roles = ["basic", "creator", "moderator", "admin"]
        role_data = []
        
        for role in roles:
            permission_ids = perm_system.db_system.get_role_permissions_from_db(role, db)  # String IDs
            role_data.append({
                "name": role,
                "permission_count": len(permission_ids),
                "permission_ids": list(permission_ids)  # String IDs
            })
        
        return success_response(
            {"roles": role_data, "total_roles": len(role_data)},
            "System roles loaded successfully"
        )
    except Exception as e:
        return error_response(f"Failed to get system roles: {str(e)}")

@router.get("/user/{user_id}/details")
async def get_user_permissions_with_details(
    user_id: int,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get user permissions with detailed information - returns string IDs"""
    try:
        permissions = db.execute_query(
            auth_query("GET_USER_PERMISSIONS_WITH_DETAILS"),
            (user_id,),
            fetch=True
        )
        
        # Convert permission IDs to string for frontend
        for perm in permissions:
            perm['permission_id'] = str(perm['permission_id'])
        
        response_data = {
            "user_id": user_id,
            "permissions": permissions,
            "total_permissions": len(permissions)
        }
        
        return success_response(response_data, "User permission details loaded")
    except Exception as e:
        return error_response(f"Failed to get user permission details: {str(e)}")

# ============ ROLE TEMPLATES ============
@router.get("/templates")
async def get_role_templates(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW))
):
    """Get all available role templates - returns string IDs"""
    try:
        # Convert template permission IDs to string for frontend
        templates_with_string_ids = {}
        for key, template in ROLE_TEMPLATES.items():
            templates_with_string_ids[key] = {
                **template,
                "permission_ids": [str(pid) for pid in template["permission_ids"]]  # Convert to string
            }
        
        return success_response(templates_with_string_ids, "Role templates loaded successfully")
    except Exception as e:
        return error_response(f"Failed to load role templates: {str(e)}")

@router.get("/templates/{template_name}")
async def get_role_template(
    template_name: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW))
):
    """Get a specific role template - returns string IDs"""
    try:
        template = ROLE_TEMPLATES.get(template_name)
        if not template:
            return error_response(f"Template '{template_name}' not found")
        
        # Convert permission IDs to string for frontend
        template_with_string_ids = {
            **template,
            "permission_ids": [str(pid) for pid in template["permission_ids"]]  # Convert to string
        }
        
        return success_response(template_with_string_ids, f"Template '{template_name}' loaded")
    except Exception as e:
        return error_response(f"Failed to load template: {str(e)}")

@router.post("/templates")
async def create_role_template(
    template_data: RoleTemplate,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS))
):
    """Create a new role template - accepts string IDs"""
    try:
        template_key = template_data.name.lower().replace(" ", "_")
        
        if template_key in ROLE_TEMPLATES:
            return error_response(f"Template '{template_key}' already exists")
        
        # Convert string IDs to int for storage
        permission_ids_int = [int(pid) for pid in template_data.permission_ids]
        
        ROLE_TEMPLATES[template_key] = {
            "name": template_data.name,
            "description": template_data.description,
            "permission_ids": permission_ids_int,  # Store as int
            "power_level": template_data.power_level
        }
        
        return success_response(message=f"Template '{template_data.name}' created successfully")
    except ValueError:
        return error_response("Invalid permission ID format")
    except Exception as e:
        return error_response(f"Failed to create template: {str(e)}")

# ============ SYSTEM & AUDIT ENDPOINTS ============
@router.get("/analysis/system")
async def get_system_power_analysis(
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Get system-wide power analysis - uses string IDs"""
    try:
        perm_system = ExplicitPermissionSystem()
        
        # Get all roles analysis
        roles = ["basic", "creator", "moderator", "admin"]
        role_analysis = []
        
        for role in roles:
            analysis = RolePermissions.get_role_power_analysis(role, db)  # Uses string IDs
            role_analysis.append(analysis)
        
        # Get overall power distribution
        overall_distribution = {
            "low": sum(role["power_distribution"]["low"] for role in role_analysis),
            "medium": sum(role["power_distribution"]["medium"] for role in role_analysis),
            "high": sum(role["power_distribution"]["high"] for role in role_analysis),
            "critical": sum(role["power_distribution"]["critical"] for role in role_analysis)
        }
        
        # Get user statistics
        user_stats = db.execute_single(
            "SELECT COUNT(*) as total_users, AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))/86400) as avg_account_age FROM users",
            fetch=True
        )
        
        # Risk assessment
        high_power_roles = [role for role in role_analysis if role["max_power"] > 80]
        
        # Get role permissions for conflict detection
        role_permissions_dict = {}
        for role in roles:
            role_permissions_dict[role] = perm_system.db_system.get_role_permissions_from_db(role, db)  # String IDs
        
        potential_conflicts = RolePermissions.find_permission_conflicts(role_permissions_dict, db)
        
        analysis_data = {
            "overall_power_distribution": overall_distribution,
            "role_analysis": role_analysis,
            "risk_assessment": {
                "high_risk_roles": [role["role"] for role in high_power_roles],
                "potential_conflicts": [conflict["message"] for conflict in potential_conflicts],
                "recommendations": [
                    "Regularly review high-power role assignments",
                    "Monitor permission conflicts between roles",
                    "Implement least privilege principle"
                ]
            },
            "system_metrics": {
                "total_roles": len(roles),
                "total_users": user_stats["total_users"] if user_stats else 0,
                "avg_account_age_days": round(user_stats["avg_account_age"], 2) if user_stats else 0
            }
        }
        
        return success_response(analysis_data, "System power analysis completed")
    except Exception as e:
        return error_response(f"Failed to generate system analysis: {str(e)}")

@router.get("/health")
async def health_check(db = Depends(get_db)):
    """System health check"""
    try:
        # Check database connectivity
        db_status = db.execute_single("SELECT 1 as status", fetch=True) is not None
        
        # Check core tables
        tables_to_check = ["users", "user_permissions", "permissions", "role_permissions"]
        table_status = {}
        
        for table in tables_to_check:
            try:
                result = db.execute_single(f"SELECT COUNT(*) as count FROM {table}", fetch=True)
                table_status[table] = result is not None
            except:
                table_status[table] = False
        
        # Get system metrics
        metrics = {}
        try:
            user_count = db.execute_single("SELECT COUNT(*) as count FROM users", fetch=True)
            permission_count = db.execute_single("SELECT COUNT(*) as count FROM permissions", fetch=True)
            role_count = db.execute_single("SELECT COUNT(DISTINCT role_key) as count FROM role_permissions", fetch=True)
            
            metrics = {
                "total_users": user_count["count"] if user_count else 0,
                "total_permissions": permission_count["count"] if permission_count else 0,
                "total_roles": role_count["count"] if role_count else 0,
                "active_sessions": 0
            }
        except:
            metrics = {"error": "Failed to fetch metrics"}
        
        overall_status = "healthy" if db_status and all(table_status.values()) else "degraded"
        
        health_data = {
            "status": overall_status,
            "services": {
                "database": db_status,
                "cache": True,
                "messaging": True
            },
            "tables": table_status,
            "metrics": metrics,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return success_response(health_data, "Health check completed")
    except Exception as e:
        return error_response(f"Health check failed: {str(e)}")

@router.get("/quick-actions")
async def get_quick_actions(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get quick actions available to the current user"""
    try:
        perm_system = ExplicitPermissionSystem()
        user_permissions = perm_system.get_user_permission_ids_with_roles(current_user.id, db)  # String IDs
        
        actions = []
        
        # Admin actions
        if str(CommonPermissionIds.ADMIN_ACCESS) in user_permissions:
            actions.extend([
                {
                    "icon": "👥",
                    "label": "Manage Users",
                    "href": "/admin/users",
                    "description": "Manage system users and permissions"
                },
                {
                    "icon": "⚙️",
                    "label": "System Settings",
                    "href": "/admin/settings",
                    "description": "Configure system-wide settings"
                },
                {
                    "icon": "📊",
                    "label": "System Analytics",
                    "href": "/admin/analytics",
                    "description": "View system performance and usage analytics"
                }
            ])
        
        # User management actions
        if str(CommonPermissionIds.USER_MANAGE) in user_permissions:
            actions.extend([
                {
                    "icon": "➕",
                    "label": "Add User",
                    "href": "/users/create",
                    "description": "Create a new user account"
                },
                {
                    "icon": "📋",
                    "label": "User Reports",
                    "href": "/users/reports",
                    "description": "Generate user activity reports"
                }
            ])
        
        # Content management actions
        if str(CommonPermissionIds.FLASHCARD_CREATE) in user_permissions:
            actions.extend([
                {
                    "icon": "📚",
                    "label": "Create Flashcards",
                    "href": "/flashcards/create",
                    "description": "Create new flashcard decks"
                },
                {
                    "icon": "📊",
                    "label": "Flashcard Analytics",
                    "href": "/flashcards/analytics",
                    "description": "View flashcard usage statistics"
                }
            ])
        
        # Always available actions
        actions.extend([
            {
                "icon": "👤",
                "label": "My Profile",
                "href": "/profile",
                "description": "View and edit your profile"
            },
            {
                "icon": "🔒",
                "label": "My Permissions",
                "href": "/profile/permissions",
                "description": "View your current permissions"
            }
        ])
        
        return success_response(
            {"actions": actions, "total_actions": len(actions)},
            "Quick actions loaded"
        )
    except Exception as e:
        return error_response(f"Failed to get quick actions: {str(e)}")

@router.get("/audit/logs")
async def get_permission_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[int] = None,
    role_name: Optional[str] = None,
    action_type: Optional[str] = None,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Get permission audit logs with filtering"""
    try:
        # Build query
        base_query = """
            SELECT 
                pa.*,
                u1.display_name as performed_by_name,
                u2.display_name as target_user_name,
                p.display_name as permission_name
            FROM permission_audit pa
            LEFT JOIN users u1 ON pa.performed_by = u1.id
            LEFT JOIN users u2 ON pa.user_id = u2.id
            LEFT JOIN permissions p ON pa.permission_id = p.id
            WHERE 1=1
        """
        params = []
        
        # Apply filters
        if start_date:
            base_query += " AND pa.performed_at >= %s"
            params.append(start_date)
        
        if end_date:
            base_query += " AND pa.performed_at <= %s"
            params.append(end_date)
        
        if user_id:
            base_query += " AND pa.user_id = %s"
            params.append(user_id)
        
        if role_name:
            base_query += " AND pa.action LIKE %s"
            params.append(f'%{role_name}%')
        
        if action_type:
            base_query += " AND pa.action LIKE %s"
            params.append(f'%{action_type}%')
        
        base_query += " ORDER BY pa.performed_at DESC LIMIT 1000"
        
        logs = db.execute_query(base_query, tuple(params), fetch=True)
        
        # Format logs
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "id": log["id"],
                "timestamp": log["performed_at"].isoformat() if hasattr(log["performed_at"], 'isoformat') else str(log["performed_at"]),
                "user_id": log["user_id"],
                "username": log["target_user_name"],
                "action": log["action"],
                "target_type": "user_permission" if log["permission_id"] else "user_role",
                "target_id": log["permission_id"] or log["user_id"],
                "target_name": log["permission_name"] or "Role Change",
                "details": {
                    "performed_by": log["performed_by_name"],
                    "performed_by_id": log["performed_by"]
                },
                "ip_address": "N/A"
            })
        
        response_data = {
            "logs": formatted_logs,
            "total_logs": len(formatted_logs),
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "role_name": role_name,
                "action_type": action_type
            }
        }
        
        return success_response(response_data, "Audit logs loaded")
    except Exception as e:
        return error_response(f"Failed to get audit logs: {str(e)}")

# ============ BULK OPERATIONS ============
@router.post("/roles/bulk-permissions")
async def bulk_update_role_permissions(
    update_data: Dict[str, Any],
    current_user: User = Depends(require_permission_id(CommonPermissionIds.ADMIN_ACCESS)),
    db = Depends(get_db)
):
    """Bulk update permissions for multiple roles - accepts string IDs"""
    try:
        updates = update_data.get("updates", [])
        results = []
        
        for update in updates:
            role_name = update.get("role_name")
            permission_ids = update.get("permission_ids", [])
            
            if not role_name or role_name not in ["basic", "creator", "moderator", "admin"]:
                results.append({
                    "role_name": role_name,
                    "success": False,
                    "message": "Invalid role name"
                })
                continue
            
            try:
                perm_system = ExplicitPermissionSystem()
                
                # Validate permission IDs (accepts string IDs)
                invalid_permissions = []
                for perm_id in permission_ids:
                    if not perm_system.validate_permission_id(perm_id, db):
                        invalid_permissions.append(perm_id)
                
                if invalid_permissions:
                    results.append({
                        "role_name": role_name,
                        "success": False,
                        "message": f"Invalid permission IDs: {invalid_permissions}"
                    })
                    continue
                
                # Save to database (handles string to int conversion)
                success = perm_system.save_role_permissions(
                    role_name, permission_ids, current_user.id, db
                )
                
                if success:
                    results.append({
                        "role_name": role_name,
                        "success": True,
                        "message": f"Updated {len(permission_ids)} permissions",
                        "permission_count": len(permission_ids)
                    })
                else:
                    results.append({
                        "role_name": role_name,
                        "success": False,
                        "message": "Failed to save permissions"
                    })
                    
            except Exception as e:
                results.append({
                    "role_name": role_name,
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
        
        success_count = sum(1 for r in results if r["success"])
        
        return success_response(
            {
                "results": results,
                "summary": {
                    "total_roles": len(updates),
                    "successful": success_count,
                    "failed": len(updates) - success_count
                }
            },
            f"Bulk update completed: {success_count} successful, {len(updates) - success_count} failed"
        )
        
    except Exception as e:
        return error_response(f"Bulk update failed: {str(e)}")
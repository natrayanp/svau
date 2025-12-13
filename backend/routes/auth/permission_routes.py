# routers/permissions_router.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from utils.database.database import DatabaseManager, get_db, DatabaseError
from utils.auth.middleware import get_current_user
from fastapi import Query
from models.auth_models import (
    UserPermissionsRequest, UserPermissionsResponse, SuccessResponse,
    User, PermissionStructureAPIResponse, RolePermissionsResponse,
    RolePermissionsUpdateRequest, PermissionValidationRequest,
    PermissionValidationResponse, AllowedPermissionsResponse,
    PowerAnalysisResponse, RoleTemplate
)
from utils.auth.permissions import require_permission_id, CommonPermissionIds, ExplicitPermissionSystem
from utils.api.response_utils import error_response, success_response
from models.permission_models import (PermissionStructure,UserModel,Role)

from models.api_models import ApiResponse,PaginatedData,PaginatedDataResponse
from utils.appwide.errors import AppException
import logging
from utils.database.query_manager import permission_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-api/permissions", tags=["permissions"])


# --------------------------
# PERMISSION STRUCTURE ENDPOINT
# --------------------------
@router.get("/structure", response_model=PermissionStructure)
async def get_permission_structure(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """
    Fetch complete permission structure from the database.

    - Fetches the current authenticated user.
    - Enforces ADMIN_ACCESS permission explicitly.
    - Returns structured JSON wrapped in ApiResponse.
    - Handles database and application errors consistently.
    """
    # Explicitly enforce permission for clarity
    #await require_permission_id(CommonPermissionIds.ADMIN_ACCESS)(current_user)
    
    try:
        # Replace with actual query or use your permission_query function        
        result = db.fetch_all(permission_query("PERMISSION_STRUCTURE_QUERY"))
        print (result)
        #if not result or 'permission_structure' not in result:
        if not result:
            raise AppException(
                message="Permission structure not found",
                code="PERMISSION_STRUCTURE_NOT_FOUND"
            )
        print('retunring the result')
        return result[0]["permission_structure"]

    except DatabaseError as e:
        logger.error(f"Database error fetching permission structure: {e.message}, query: {e.query}")
        raise AppException(
            message="Could not load permission structure",
            code="DB_PERMISSION_STRUCTURE_ERROR"
        )
    except AppException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_permission_structure: {e}")
        raise AppException(
            message="An unexpected error occurred",
            code="PERMISSION_STRUCTURE_UNKNOWN_ERROR"
        )


# ----------------------------------------------------
# USER ENDPOINTS -- START
# ----------------------------------------------------

@router.get("/users", response_model=PaginatedDataResponse[UserModel])
async def get_organization_users(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get active users for the current user's organization with their roles, paginated.
    """
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        result = user_service.get_organization_users(
            current_user_id=current_user.user_id,
            offset=offset,
            limit=limit
        )
        
        return result
        

        
    except AppException as e:
        raise
    except DatabaseError as e:
        logger.error(f"Database error fetching organization users: {e.message}, query: {e.query}")
        raise AppException(
            message="Could not load organization users",
            code="DB_ORG_USERS_ERROR"
        )
    except Exception as e:
        logger.exception(f"Unexpected error in get_organization_users: {e}")
        raise AppException(
            message="An unexpected error occurred",
            code="ORG_USERS_UNKNOWN_ERROR"
        )


@router.post("/users/create", response_model=PaginatedDataResponse[UserModel])
async def bulk_create_users(
    request_body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Create multiple users in an all-or-nothing transaction.
    
    Request body:
    {
        "data": [
            {
                "email": "user1@example.com",
                "display_name": "User One",
                "roles": ["1", "2"],
                "department": "Engineering",
                "location": "SF",
                "status": "AC",
                "status_effective_from": "2024-01-01T00:00:00.000Z"
            },
            {
                "email": "user2@example.com",
                "display_name": "User Two",
                "roles": ["3"]
            }
        ],
        "offset": 0,
        "limit": 20
    }
    """
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        # Get user's organization
        org_id, _ = user_service.get_user_organization(current_user.user_id)

        # Get parameters
        users_data = request_body.get("data", [])
        offset = request_body.get("offset", 0)
        limit = request_body.get("limit", 20)

        # Validate offset and limit
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20

        if not users_data:
            raise AppException(
                message="No users provided for creation",
                code="NO_USERS_PROVIDED"
            )

        # Execute bulk create (all-or-nothing)
        operation_result = user_service.bulk_create_users(
            org_id=org_id,
            users_data=users_data,
            created_by=current_user.user_id
        )
        
        # Get updated users list
        updated_users = user_service.get_organization_users(
            current_user_id=current_user.user_id,
            offset=offset,
            limit=limit
        )

        # Add operation summary to response
        response_data = updated_users["data"]
        response_data["operation_metadata"] = operation_result
        
        return {
            "data": response_data,
            "operation_metadata": operation_result
        }
                
    except AppException as e:
        # Transaction was rolled back
        logger.warning(f"Bulk create failed: {e.message}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in bulk user creation: {e}")
        raise AppException(
            message="Failed to create users in bulk",
            code="BULK_USER_CREATE_ERROR"
        )


@router.put("/users/update", response_model=PaginatedDataResponse[UserModel])
async def bulk_update_users(
    request_body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Bulk update multiple users with roles and additional fields.
    
    Request body:
    {
        "data": [
            {
                "user_id": 123,
                "roles": ["1", "2", "3"],
                "department": "Engineering",
                "location": "San Francisco",
                "status": "AC",
                "status_effective_from": "2024-01-15T00:00:00.000Z"
            },
            {
                "user_id": 124,
                "roles": ["1", "2"]
            }
        ],
        "offset": 0,
        "limit": 20
    }
    """
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        # Get user's organization
        org_id, _ = user_service.get_user_organization(current_user.user_id)

        # Get parameters
        users_data = request_body.get("data", [])
        offset = request_body.get("offset", 0)
        limit = request_body.get("limit", 20)

        print(users_data)
        
        # Validate offset and limit
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20

        if not users_data:
            raise AppException(
                message="No users provided for update",
                code="NO_USERS_PROVIDED"
            )

        # Execute bulk update (all-or-nothing)
        operation_result = user_service.bulk_update_users(
            org_id=org_id,
            users_data=users_data,
            updated_by=current_user.user_id
        )
        
        # Get updated users list
        updated_users = user_service.get_organization_users(
            current_user_id=current_user.user_id,
            offset=offset,
            limit=limit
        )

        # Add operation summary to response
        response_data = updated_users["data"]
        response_data["operation_metadata"] = operation_result
        
        return {
            "data": response_data,
            "operation_metadata": operation_result
        }
                
    except AppException as e:
        # Transaction was rolled back
        logger.warning(f"Bulk update failed: {e.message}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in bulk user update: {e}")
        raise AppException(
            message="Failed to update users in bulk",
            code="BULK_USER_UPDATE_ERROR"
        )


@router.delete("/users/delete", response_model=PaginatedDataResponse[UserModel])
async def bulk_delete_users(
    request_body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Delete multiple users in an all-or-nothing transaction.
    
    Request body:
    {
        "user_ids": [123, 124, 125],
        "hard_delete": false,
        "offset": 0,
        "limit": 20
    }
    """
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        # Get user's organization
        org_id, _ = user_service.get_user_organization(current_user.user_id)

        # Get parameters
        user_ids = request_body.get("user_ids", [])
        hard_delete = request_body.get("hard_delete", False)
        offset = request_body.get("offset", 0)
        limit = request_body.get("limit", 20)

        # Validate offset and limit
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20

        if not user_ids:
            raise AppException(
                message="No user IDs provided for deletion",
                code="NO_USER_IDS_PROVIDED"
            )

        # Validate user IDs
        validated_user_ids = []
        for i, user_id in enumerate(user_ids):
            try:
                user_id_int = int(user_id)
                validated_user_ids.append(user_id_int)
            except (ValueError, TypeError):
                raise AppException(
                    message=f"Invalid user ID '{user_id}' at index {i}",
                    code="INVALID_USER_ID"
                )

        # Execute bulk delete (all-or-nothing)
        operation_result = user_service.bulk_delete_users(
            org_id=org_id,
            user_ids=validated_user_ids,
            deleted_by=current_user.user_id,
            hard_delete=hard_delete
        )
        
        # Get updated users list
        updated_users = user_service.get_organization_users(
            current_user_id=current_user.user_id,
            offset=offset,
            limit=limit
        )

        # Add operation summary to response
        response_data = updated_users["data"]
        response_data["operation_metadata"] = operation_result
        
        return {
            "data": response_data,
            "operation_metadata": operation_result
        }
                
    except AppException as e:
        # Transaction was rolled back
        logger.warning(f"Bulk delete failed: {e.message}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in bulk user deletion: {e}")
        raise AppException(
            message="Failed to delete users in bulk",
            code="BULK_USER_DELETE_ERROR"
        )


@router.get("/users/{user_id}/details")
async def get_user_details(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get detailed information for a specific user."""
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        result = user_service.get_user_details(
            user_id=user_id,
            requesting_user_id=current_user.user_id
        )
        
        return result
        
    except AppException as e:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting user details: {e}")
        raise AppException(
            message="Failed to get user details",
            code="USER_DETAILS_ERROR"
        )


@router.get("/users/{user_id}/power-analysis")
async def get_user_power_analysis(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Get power analysis for a user based on assigned roles."""
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        result = user_service.get_user_power_analysis(
            user_id=user_id,
            requesting_user_id=current_user.user_id
        )
        
        return result
        
    except AppException as e:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in power analysis: {e}")
        raise AppException(
            message="Failed to analyze user power",
            code="POWER_ANALYSIS_ERROR"
        )


@router.get("/users/search")
async def search_users(
    search: str = Query(..., min_length=1, description="Search term for name, email, or UID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Search users within the organization."""
    try:
        from routes.auth.services.user_service import UserService
        user_service = UserService(db)
        
        # Get user's organization
        org_id, _ = user_service.get_user_organization(current_user.user_id)
        
        result = user_service.search_users(
            org_id=org_id,
            search_term=search,
            offset=offset,
            limit=limit
        )
        
        return result
        
    except AppException as e:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error searching users: {e}")
        raise AppException(
            message="Failed to search users",
            code="USER_SEARCH_ERROR"
        )

# ----------------------------------------------------
# USER ENDPOINTS -- END
# ----------------------------------------------------

# ----------------------------------------------------
# ORGANIZATION ROLES ENDPOINT -- START
# ----------------------------------------------------
@router.get("/roles", response_model=PaginatedDataResponse[Role])
async def get_organization_roles(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get roles for the current user's organization with package filtering.
    """
    try:
        from routes.auth.services.role_service import RoleService
        role_service = RoleService(db)
         
        # Get user's organization
        role_data = role_service.get_role_for_organisation(current_user.user_id, offset, limit)
    
        # FIX: Corrected condition (was 'and', should be 'or')
        if not role_data or 'roles_data' not in role_data:
            raise AppException(
                message="No roles found for your organization",
                code="ORG_ROLES_NOT_FOUND"
            )

        paginated_roles = role_data['roles_data']
        #paginated_roles["operation_metadata"] = {"success": True, "entity": "roles", "operation": "get", "message": "Roles fetched successfully", "count": len(paginated_roles), "ids": 1}
        #print("paginated_roles", paginated_roles)
        result = {"data":paginated_roles, "operation_metadata": {"success": True, "entity": "roles", "operation": "get", "message": "Roles fetched successfully", "count": len(paginated_roles), "ids": ['1']}}
        
        return result
       
    except DatabaseError as e:
        logger.error(f"Database error fetching organization roles: {e.message}, query: {e.query}")
        raise AppException(
            message="Could not load organization roles",
            code="DB_ORG_ROLES_ERROR"
        )
    except AppException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_organization_roles: {e}")
        raise AppException(
            message="An unexpected error occurred",
            code="ORG_ROLES_UNKNOWN_ERROR"
        )


@router.put("/roles/update", response_model=PaginatedDataResponse[Role])
async def update_organization_roles(
    request_body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Update multiple roles.
    
    Request body:
    {
        "roles": [
            {
                "role_id": 123,
                "display_name": "Updated Name",
                "permissions": [...]
            },
            {
                "role_id": 124,
                "description": "Updated Description"
            }
        ],
        "offset": 0,
        "limit": 20
    }
    """
    try:
        from routes.auth.services.role_service import RoleService
        role_service = RoleService(db)
        
        # Get user's organization
        org_id, _ = role_service.get_user_organization(current_user.user_id)

        # Get parameters
        roles_data = request_body.get("data", [])
        offset = request_body.get("offset", 0)
        limit = request_body.get("limit", 20)

        # Validate offset and limit (match your other endpoints)
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20

        if not roles_data:
            raise AppException(
                message="No roles provided for update",
                code="NO_ROLES_PROVIDED"
            )

        # Execute bulk update (all-or-nothing)
        operation_result = role_service.bulk_update_roles(
            org_id=org_id,
            roles_data=roles_data,
            updated_by=current_user.user_id
        )
        
        # Get user's organization
        role_data = role_service.get_role_for_organisation(current_user.user_id, offset, limit)
    
        # FIX: Corrected condition (was 'and', should be 'or')
        if not role_data or 'roles_data' not in role_data:
            raise AppException(
                message="No roles found for your organization",
                code="ORG_ROLES_NOT_FOUND"
            )

        paginated_roles = role_data['roles_data']
        #paginated_roles["operation_metadata"] = {"success": True, "entity": "roles", "operation": "get", "message": "Roles fetched successfully", "count": len(paginated_roles), "ids": 1}
        #print("paginated_roles", paginated_roles)
        result = {"data":paginated_roles, "operation_metadata": operation_result}
        
        return result
                
    except AppException as e:
        # Transaction was rolled back
        logger.warning(f"Bulk update failed: {e.message}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in bulk role update: {e}")
        raise AppException(
            message="Failed to update roles in bulk",
            code="BULK_ROLE_UPDATE_ERROR"
        )

@router.post("/roles/create", response_model=PaginatedData[Role])
async def bulk_create_organization_roles(
    request_body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Create multiple roles in an all-or-nothing transaction.
    
    Request body:
    {
        "roles": [
            {
                "display_name": "New Role 1",
                "description": "Role description 1",
                "permissions": [
                    {
                        "permissstruct_id": "456",
                        "granted_action_key": ["read", "write"]
                    }
                ]
            },
            {
                "display_name": "New Role 2",
                "description": "Role description 2"
            }
        ],
        "offset": 0,      # optional, defaults to 0
        "limit": 20       # optional, defaults to 20
    }
    
    Behavior:
    - All creations succeed → returns paginated role data (including new roles)
    - Any creation fails → entire transaction rolls back, returns error
    """
    try:
        from routes.auth.services.role_service import RoleService
        role_service = RoleService(db)
        
        # Get user's organization
        org_id, _ = role_service.get_user_organization(current_user.user_id)
        
        # Get parameters with validation
        roles_data = request_body.get("roles", [])
        offset = request_body.get("offset", 0)
        limit = request_body.get("limit", 20)
        
        # Validate offset and limit
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20

        if not roles_data:
            raise AppException(
                message="No roles provided for creation",
                code="NO_ROLES_PROVIDED"
            )
        
        # Validate required fields before transaction
        for i, role_data in enumerate(roles_data):
            display_name = role_data.get("display_name")
            if not display_name or not display_name.strip():
                raise AppException(
                    message=f"Missing or empty display_name at index {i}",
                    code="MISSING_DISPLAY_NAME"
                )
            
            # Check for duplicate names in the request
            display_name_clean = display_name.strip()
            duplicate_check = [r.get("display_name", "").strip() == display_name_clean 
                             for r in roles_data[:i]]
            if any(duplicate_check):
                raise AppException(
                    message=f"Duplicate role name '{display_name_clean}' in request",
                    code="DUPLICATE_ROLE_NAME"
                )

        # Execute bulk create (all-or-nothing)
        operation_result = role_service.bulk_create_roles(
            org_id=org_id,
            roles_data=roles_data,
            created_by=current_user.user_id
        )
        
        # Log successful operation
        logger.info(
            f"User {current_user.user_id} bulk created {operation_result['created_count']} roles. "
            f"Created IDs: {operation_result['created_ids']}"
        )
        
        # Get paginated data after successful creation
        paginated_result = db.fetch_one(
            permission_query("ORGANIZATION_ROLES_QUERY"),
            {
                "current_user_id": current_user.user_id,
                "offset": offset,
                "limit": limit
            }
        )

        if not paginated_result or 'roles_data' not in paginated_result:
            # This shouldn't happen if create succeeded, but handle gracefully
            raise AppException(
                message="Failed to fetch roles data after creation",
                code="ROLES_FETCH_ERROR"
            )
        
        # Add operation summary to response
        roles_response = paginated_result['roles_data']
        """roles_response['operation_metadata'] = {
            "operation": "create_roles",
            "count": len(roles_data),
            "ids": [role['role_id'] for role in roles_data],
        }"""

        return {
            "data": roles_response,
            "operation_metadata": operation_result            
        }

        
    except AppException as e:
        # Transaction was rolled back
        logger.warning(f"Bulk create failed for user {current_user.user_id}: {e.message}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in bulk role creation for user {current_user.user_id}: {e}")
        raise AppException(
            message="Failed to create roles in bulk",
            code="BULK_ROLE_CREATE_ERROR"
        )


@router.delete("/roles/delete", response_model=PaginatedData[Role])
async def bulk_delete_organization_roles(
    request_body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Delete multiple roles in an all-or-nothing transaction.
    
    Request body:
    {
        "role_ids": [123, 124, 125],
        "hard_delete": false,  # optional, default false (soft delete)
        "offset": 0,           # optional, defaults to 0
        "limit": 20            # optional, defaults to 20
    }
    
    Behavior:
    - All deletions succeed → returns paginated role data (without deleted roles)
    - Any deletion fails → entire transaction rolls back, returns error
    """
    try:
        from routes.auth.services.role_service import RoleService
        role_service = RoleService(db)
        
        # Get user's organization
        org_id, _ = role_service.get_user_organization(current_user.user_id)
        
        # Get parameters with validation
        role_ids = request_body.get("role_ids", [])
        hard_delete = request_body.get("hard_delete", False)
        offset = request_body.get("offset", 0)
        limit = request_body.get("limit", 20)
        
        # Validate offset and limit
        if offset < 0:
            offset = 0
        if limit < 1 or limit > 100:
            limit = 20

        if not role_ids:
            raise AppException(
                message="No role IDs provided for deletion",
                code="NO_ROLE_IDS_PROVIDED"
            )
        
        # Validate role IDs are integers
        validated_role_ids = []
        for i, role_id in enumerate(role_ids):
            try:
                role_id_int = int(role_id)
                validated_role_ids.append(role_id_int)
            except (ValueError, TypeError):
                raise AppException(
                    message=f"Invalid role ID '{role_id}' at index {i}",
                    code="INVALID_ROLE_ID"
                )

        # Execute bulk delete (all-or-nothing)
        operation_result = role_service.bulk_delete_roles(
            org_id=org_id,
            role_ids=validated_role_ids,
            deleted_by=current_user.user_id,
            hard_delete=hard_delete
        )
        
        # Log successful operation
        logger.info(
            f"User {current_user.user_id} bulk deleted {operation_result['deleted_count']} roles. "
            f"Deleted IDs: {operation_result['deleted_ids']}, Hard delete: {hard_delete}"
        )
        
        # Get paginated data after successful deletion
        paginated_result = db.fetch_one(
            permission_query("ORGANIZATION_ROLES_QUERY"),
            {
                "current_user_id": current_user.user_id,
                "offset": offset,
                "limit": limit
            }
        )

        if not paginated_result or 'roles_data' not in paginated_result:
            raise AppException(
                message="Failed to fetch roles data after deletion",
                code="ROLES_FETCH_ERROR"
            )
        
        # Add operation summary to response
        roles_response = paginated_result['roles_data']

        return {
            "data": roles_response,
            "operation_metadata": operation_result            
        }
        
    except AppException as e:
        # Transaction was rolled back
        logger.warning(f"Bulk delete failed for user {current_user.user_id}: {e.message}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in bulk role deletion: {e}")
        raise AppException(
            message="Failed to delete roles in bulk",
            code="BULK_ROLE_DELETE_ERROR"
        )

# ----------------------------------------------------
# ORGANIZATION ROLES ENDPOINT -- END
# ----------------------------------------------------


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


# ============ ROLE TEMPLATES ============
@router.get("/templates")
async def get_role_templates(
    template_keys: Optional[str] = None,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get role templates - all, single, or multiple templates with organization filtering"""
    try:
        # Parse template_keys parameter if provided
        template_list = None
        if template_keys:
            template_list = [key.strip() for key in template_keys.split(",") if key.strip()]
        
        # Determine which query to use
        if template_list is None:
            # Get ALL templates
            result = await db.fetch_one(
                permission_query("GET_ALL_ROLE_TEMPLATES"),
                (current_user.id,),  # Pass current user ID for organization context
                fetch=True
            )
            message = "All role templates loaded successfully"
            
        elif len(template_list) == 1:
            # Get SINGLE template
            result = await db.fetch_one(
                permission_query("GET_SINGLE_ROLE_TEMPLATE"),
                (current_user.id, template_list[0]),  # user_id + specific template
                fetch=True
            )
            message = f"Template '{template_list[0]}' loaded successfully"
            
        else:
            # Get MULTIPLE templates
            result = await db.fetch_one(
                permission_query("GET_MULTIPLE_ROLE_TEMPLATES"),
                (current_user.id, template_list),  # user_id + array of templates
                fetch=True
            )
            message = f"{len(template_list)} templates loaded successfully"
        
        if result:
            return success_response(result, message)
        else:
            return success_response(
                {"templates": [], "summary": {"total_templates": 0}},
                "No templates found for your organization"
            )
            
    except Exception as e:
        logger.error(f"Failed to load role templates: {str(e)}")
        return error_response(f"Failed to load role templates: {str(e)}")


@router.get("/templates/{template_key}")
async def get_role_template_by_key(
    template_key: str,
    current_user: User = Depends(require_permission_id(CommonPermissionIds.USER_VIEW)),
    db = Depends(get_db)
):
    """Get specific role template details by template key"""
    try:
        # Get template with organization context and package filtering
        template_result = await db.fetch_one(
            permission_query("GET_SINGLE_ROLE_TEMPLATE"),
            (current_user.id, template_key),  # user_id + template_key
            fetch=True
        )
        
        if not template_result or not template_result.get('template'):
            return error_response(f"Template '{template_key}' not found or not accessible")
        
        # Get template usage statistics (optional)
        usage_stats = await db.fetch_one(
            permission_query("GET_TEMPLATE_USAGE_STATS_BY_KEY"),
            (template_key,),
            fetch=True
        )
        
        response_data = {
            "template": template_result['template'],
            "usage_stats": usage_stats or {}
        }
        
        return success_response(
            response_data,
            f"Template '{template_key}' loaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to load template {template_key}: {str(e)}")
        return error_response(f"Failed to load template: {str(e)}")


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
        user_stats = await db.fetch_one(
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
        db_status = await db.fetch_one("SELECT 1 as status", fetch=True) is not None
        
        # Check core tables
        tables_to_check = ["users", "user_permissions", "permissions", "role_permissions"]
        table_status = {}
        
        for table in tables_to_check:
            try:
                result = await db.fetch_one(f"SELECT COUNT(*) as count FROM {table}", fetch=True)
                table_status[table] = result is not None
            except:
                table_status[table] = False
        
        # Get system metrics
        metrics = {}
        try:
            user_count = await db.fetch_one("SELECT COUNT(*) as count FROM users", fetch=True)
            permission_count = await db.fetch_one("SELECT COUNT(*) as count FROM permissions", fetch=True)
            role_count = await db.fetch_one("SELECT COUNT(DISTINCT role_id) as count FROM role_permissions", fetch=True)
            
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
        
        logs = await db.fetch_all(base_query, tuple(params), fetch=True)
        
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
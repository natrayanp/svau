# services/role_service.py

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from utils.database.database import DatabaseManager
from utils.database.query_manager import permission_query
from utils.appwide.errors import AppException

logger = logging.getLogger(__name__)


class RoleService:
    """Service layer for role-related operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ======================================================
    # COMMON METHODS
    # ======================================================

    def get_user_organization(self, user_id: int) -> Tuple[int, Dict[str, Any]]:
        result = self.db.fetch_one(
            permission_query("GET_USER_ORGANIZATION"),
            {"user_id": user_id}
        )

        if not result:
            raise AppException("User organization not found", "ORG_NOT_FOUND")

        return result["org_id"], result

    def verify_role_access(self, role_id: int, org_id: int) -> bool:
        check = self.db.fetch_one(
            permission_query("VERIFY_ROLE_ORGANIZATION"),
            {"role_id": role_id, "org_id": org_id}
        )
        return bool(check)

    def check_role_name_exists(self, org_id: int, display_name: str) -> bool:
        existing = self.db.fetch_one(
            permission_query("CHECK_ROLE_NAME_EXISTS"),
            {"org_id": org_id, "display_name": display_name}
        )
        return bool(existing)

    # ======================================================
    # ROLE CRUD
    # ======================================================

    def _update_role_metadata(
        self,
        role_id: int,
        display_name: Optional[str],
        description: Optional[str],
        updated_by: int,
    ):
        fields = []
        params = {"role_id": role_id, "updated_by": updated_by}

        if display_name is not None:
            fields.append("display_name = %(display_name)s")
            params["display_name"] = display_name.strip()

        if description is not None:
            fields.append("description = %(description)s")
            params["description"] = description.strip()

        if not fields:
            return

        query = permission_query("UPDATE_ROLE_METADATA").format(
            update_fields=", ".join(fields)
        )

        self.db.execute(query, params)

    def update_role_permissions(self, role_id: int, permissions: List[Dict[str, Any]]):
        if not permissions:
            return

        structure_ids = []

        for perm in permissions:
            structure_id = int(perm.get("permissstruct_id"))
            granted = json.dumps(perm.get("granted_action_key", []))

            structure_ids.append(structure_id)

            self.db.execute(
                permission_query("UPSERT_ROLE_PERMISSION"),
                {
                    "role_id": role_id,
                    "structure_id": structure_id,
                    "granted_actions": granted,
                },
            )

        # Remove permissions not in update
        self.db.execute(
            permission_query("REMOVE_OLD_PERMISSIONS"),
            {"role_id": role_id, "structure_ids": tuple(structure_ids)},
        )

    def get_role_for_organisation(self, user_id: int, offset: int, limit: int):
        print("user_id", user_id)
        result = self.db.fetch_one(
            permission_query("ORGANIZATION_ROLES_QUERY"),
            {"current_user_id": user_id, "offset": offset, "limit": limit}
        )
        if not result:
            raise AppException(
                message="No roles found for your organization",
                code="ORG_ROLES_NOT_FOUND"
            )
        
        response_data = {"roles_data": result['roles_data'], "operation_metadata": {"performed_by": user_id}}

        return response_data


    def _get_role_details(self, role_id: int) -> Dict[str, Any]:
        role = self.db.fetch_one(
            """
            SELECT role_id, org_id, display_name, description,
                   is_system_role, created_at, updated_at
            FROM roles
            WHERE role_id = %(role_id)s
            """,
            {"role_id": role_id},
        )


        if not role:
            raise AppException("Role not found", "ROLE_NOT_FOUND")

        perm_count = self.db.fetch_one(
            "SELECT COUNT(*) AS ct FROM role_permissions WHERE role_id=%(role_id)s AND status='AC'",
            {"role_id": role_id},
        )

        user_count = self.db.fetch_one(
            "SELECT COUNT(DISTINCT user_id) AS ct FROM user_roles WHERE role_id=%(role_id)s",
            {"role_id": role_id},
        )

        role["permission_count"] = perm_count["ct"]
        role["user_count"] = user_count["ct"]

        return role


    # ======================================================
    # BULK CREATE
    # ======================================================

    def bulk_create_roles(self, org_id: int, roles_data: List[Dict[str, Any]], created_by: int):
        created = []
        errors = []

        with self.db.transaction():
            for i, role in enumerate(roles_data):
                try:
                    display_name = role.get("display_name")
                    if not display_name:
                        errors.append({"index": i, "error": "Missing display_name"})
                        continue

                    new_role = self.db.execute_returning(
                        permission_query("CREATE_NEW_ROLE"),
                        {
                            "org_id": org_id,
                            "display_name": display_name,
                            "description": role.get("description", ""),
                            "created_by": created_by,
                        },
                    )

                    role_id = new_role["role_id"]
                    created.append(role_id)

                    if role.get("permissions"):
                        self.update_role_permissions(role_id, role["permissions"])

                except Exception as e:
                    errors.append({"index": i, "error": str(e), "data": role})

        return {
            "success": True,
            "entity": "roles",
            "operation": "create",
            "count": len(created),
            "ids": created,
            "message": f"Successfully created {len(created)} roles"
        }

    # ======================================================
    # BULK UPDATE
    # ======================================================

    def bulk_update_roles(
        self,
        org_id: int,
        roles_data: List[Dict[str, Any]],
        updated_by: int
    ) -> Dict[str, Any]:
        """
        Update multiple roles in a single transaction.
        ALL updates succeed or NONE do (all-or-nothing).
        
        Returns operation summary only (no paginated data here).
        """
        updated_ids = []
        
        with self.db.transaction():
            for i, role in enumerate(roles_data):
                try:
                    print("role", role)
                    role_id = role.get("role_id")
                    if not role_id:
                        raise AppException(
                            message=f"Missing role_id at index {i}",
                            code="MISSING_ROLE_ID"
                        )
                    
                    role_id_int = int(role_id)
                    
                    # Verify access
                    if not self.verify_role_access(role_id_int, org_id):
                        raise AppException(
                            message=f"Role {role_id} not found or access denied",
                            code="ROLE_ACCESS_DENIED"
                        )
                    
                    # Update metadata if provided
                    if "display_name" in role or "description" in role:
                        self._update_role_metadata(
                            role_id_int,
                            role.get("display_name"),
                            role.get("description"),
                            updated_by,
                        )
                    
                    # Update permissions if provided
                    if role.get("permissions") is not None:
                        self.update_role_permissions(role_id_int, role["permissions"])
                    
                    updated_ids.append(role_id_int)
                    
                except AppException:
                    # Re-raise AppException to abort transaction
                    raise
                except Exception as e:
                    # Convert unexpected errors to AppException
                    logger.error(f"Unexpected error updating role at index {i}: {e}")
                    raise AppException(
                        message=f"Failed to update role at index {i}: {str(e)}",
                        code="ROLE_UPDATE_ERROR"
                    )
        
        # If we get here, transaction committed successfully
        return {
            "success": True,
            "entity": "roles",
            "operation": "update",
            "count": len(updated_ids),
            "ids": [str(role_id) for role_id in updated_ids],
            "message": f"Successfully updated {len(updated_ids)} roles"
        }



    # ======================================================
    # BULK DELETE
    # ======================================================
    def bulk_delete_roles(
        self,
        org_id: int,
        role_ids: List[int],
        deleted_by: int,
        hard_delete: bool = False
    ) -> Dict[str, Any]:
        """
        All-or-nothing bulk deletion of multiple roles.
        
        Either ALL roles are deleted successfully, or NONE are (transaction rolls back).
        
        Args:
            org_id: Organization ID
            role_ids: List of role IDs to delete
            deleted_by: User ID performing the deletion
            hard_delete: If True, permanently delete; if False, soft delete (default)
        
        Returns:
            Summary of successful operation
        """
        deleted_count = 0
        deleted_role_ids = []
        
        with self.db.transaction():
            for role_id in role_ids:
                try:
                    # Verify role belongs to organization and is deletable
                    if not self.verify_role_access(role_id, org_id):
                        raise AppException(
                            message=f"Role {role_id} not found or access denied",
                            code="ROLE_ACCESS_DENIED"
                        )
                    
                    # Check if it's a system role (should not be deleted)
                    role_check = self.db.fetch_one(
                        "SELECT is_system_role FROM roles WHERE role_id = %(role_id)s AND org_id = %(org_id)s",
                        {"role_id": role_id, "org_id": org_id}
                    )
                    
                    if role_check and role_check.get("is_system_role"):
                        raise AppException(
                            message=f"Cannot delete system role {role_id}",
                            code="CANNOT_DELETE_SYSTEM_ROLE"
                        )
                    
                    # Check if role has assigned users
                    user_count = self.db.fetch_one(
                        "SELECT COUNT(*) as count FROM user_roles WHERE role_id = %(role_id)s",
                        {"role_id": role_id}
                    )
                    
                    if user_count and user_count.get("count", 0) > 0:
                        raise AppException(
                            message=f"Role {role_id} has {user_count['count']} assigned users. "
                                f"Please reassign users before deleting.",
                            code="ROLE_HAS_USERS"
                        )
                    
                    # Perform deletion
                    query = permission_query("HARD_DELETE_ROLE" if hard_delete else "SOFT_DELETE_ROLE")
                    result = self.db.execute_returning(
                        query,
                        {
                            "role_id": role_id,
                            "org_id": org_id,
                            "updated_by": deleted_by
                        }
                    )
                    
                    if not result:
                        raise AppException(
                            message=f"Failed to delete role {role_id}",
                            code="ROLE_DELETE_FAILED"
                        )
                    
                    deleted_count += 1
                    deleted_role_ids.append(role_id)
                    
                except AppException:
                    # Re-raise AppException to maintain transaction rollback
                    raise
                except Exception as e:
                    # Convert unexpected errors to AppException
                    logger.error(f"Unexpected error deleting role {role_id}: {e}")
                    raise AppException(
                        message=f"Failed to delete role {role_id}: {str(e)}",
                        code="ROLE_DELETE_ERROR"
                    )
        
        # If we reach here, transaction committed successfully
        return {
            "success": True,
            "entity": "roles",
            "operation": "delete",
            "count": deleted_count,
            "ids": deleted_role_ids,
            "message": f"Successfully deleted {deleted_count} roles"
        }
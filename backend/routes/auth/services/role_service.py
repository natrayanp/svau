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
            raise AppException(
                message="User organization not found",
                code="ORG_NOT_FOUND",
                status_code=404
            )

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
    # ROLE CRUD HELPERS
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

        self.db.execute(
            permission_query("REMOVE_OLD_PERMISSIONS"),
            {"role_id": role_id, "structure_ids": tuple(structure_ids)},
        )

    # ======================================================
    # READ
    # ======================================================

    def get_role_for_organisation(self, user_id: int, offset: int, limit: int):
        result = self.db.fetch_one(
            permission_query("ORGANIZATION_ROLES_QUERY"),
            {"current_user_id": user_id, "offset": offset, "limit": limit}
        )

        if not result:
            raise AppException(
                message="No roles found for your organization",
                code="ORG_ROLES_NOT_FOUND",
                status_code=404
            )

        return {
            "roles_data": result["roles_data"],
            "operation_metadata": {"performed_by": user_id}
        }

    # ======================================================
    # BULK CREATE
    # ======================================================

    def bulk_create_roles(self, org_id: int, roles_data: List[Dict[str, Any]], created_by: int):
        created = []

        with self.db.transaction():
            for i, role in enumerate(roles_data):
                display_name = role.get("display_name")

                if not display_name:
                    raise AppException(
                        message=f"Missing display_name at index {i}",
                        code="MISSING_DISPLAY_NAME",
                        status_code=400
                    )

                try:
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
                    logger.error(f"Unexpected error creating role at index {i}: {e}")
                    raise AppException(
                        message="Failed to create role",
                        code="ROLE_CREATE_ERROR",
                        status_code=500
                    )

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

    def bulk_update_roles(self, org_id: int, roles_data: List[Dict[str, Any]], updated_by: int):
        updated_ids = []

        with self.db.transaction():
            for i, role in enumerate(roles_data):
                role_id = role.get("role_id")

                if not role_id:
                    raise AppException(
                        message=f"Missing role_id at index {i}",
                        code="MISSING_ROLE_ID",
                        status_code=400
                    )

                role_id = int(role_id)

                if not self.verify_role_access(role_id, org_id):
                    raise AppException(
                        message=f"Role {role_id} not found or access denied",
                        code="ROLE_ACCESS_DENIED",
                        status_code=404
                    )

                try:
                    if "display_name" in role or "description" in role:
                        self._update_role_metadata(
                            role_id,
                            role.get("display_name"),
                            role.get("description"),
                            updated_by,
                        )

                    if role.get("permissions") is not None:
                        self.update_role_permissions(role_id, role["permissions"])

                    updated_ids.append(role_id)

                except Exception as e:
                    logger.error(f"Unexpected error updating role {role_id}: {e}")
                    raise AppException(
                        message=f"Failed to update role {role_id}",
                        code="ROLE_UPDATE_ERROR",
                        status_code=500
                    )

        return {
            "success": True,
            "entity": "roles",
            "operation": "update",
            "count": len(updated_ids),
            "ids": updated_ids,
            "message": f"Successfully updated {len(updated_ids)} roles"
        }

    # ======================================================
    # BULK DELETE
    # ======================================================

    def bulk_delete_roles(self, org_id: int, role_ids: List[int], deleted_by: int, hard_delete: bool = False):
        deleted_ids = []

        with self.db.transaction():
            for role_id in role_ids:

                if not self.verify_role_access(role_id, org_id):
                    raise AppException(
                        message=f"Role {role_id} not found or access denied",
                        code="ROLE_ACCESS_DENIED",
                        status_code=404
                    )

                role_check = self.db.fetch_one(
                    "SELECT is_system_role FROM roles WHERE role_id=%(role_id)s AND org_id=%(org_id)s",
                    {"role_id": role_id, "org_id": org_id}
                )

                if role_check and role_check.get("is_system_role"):
                    raise AppException(
                        message=f"Cannot delete system role {role_id}",
                        code="CANNOT_DELETE_SYSTEM_ROLE",
                        status_code=409
                    )

                user_count = self.db.fetch_one(
                    "SELECT COUNT(*) AS count FROM user_roles WHERE role_id=%(role_id)s",
                    {"role_id": role_id}
                )

                if user_count and user_count["count"] > 0:
                    raise AppException(
                        message=f"Role {role_id} has {user_count['count']} assigned users. "
                                f"Please reassign users before deleting.",
                        code="ROLE_HAS_USERS",
                        status_code=409
                    )

                try:
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
                            code="ROLE_DELETE_FAILED",
                            status_code=409
                        )

                    deleted_ids.append(role_id)

                except AppException:
                    raise

                except Exception as e:
                    logger.error(f"Unexpected error deleting role {role_id}: {e}")
                    raise AppException(
                        message="An unexpected error occurred while deleting the role",
                        code="ROLE_DELETE_ERROR",
                        status_code=500
                    )

        return {
            "success": True,
            "entity": "roles",
            "operation": "delete",
            "count": len(deleted_ids),
            "ids": deleted_ids,
            "message": f"Successfully deleted {len(deleted_ids)} roles"
        }

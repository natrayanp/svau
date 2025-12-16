"""
User Service - Handles user-related operations including role assignments and additional fields.
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from utils.database.database import DatabaseManager
from utils.database.query_manager import permission_query
from utils.appwide.errors import AppException
from queries.user_queries import *

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user-related operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ======================================================
    # COMMON METHODS
    # ======================================================

    def get_user_organization(self, user_id: int) -> Tuple[int, Dict[str, Any]]:
        """Get organization for a user."""
        result = self.db.fetch_one(
            permission_query("GET_USER_ORGANIZATION"),
            {"user_id": user_id}
        )

        if not result:
            raise AppException("User organization not found", "ORG_NOT_FOUND", status_code=404)

        return result["org_id"], result

    def verify_user_access(self, target_user_id: int, org_id: int) -> bool:
        """Verify if a user belongs to the organization."""
        check = self.db.fetch_one(
            permission_query("VERIFY_USER_ACCESS"),
            {"user_id": target_user_id, "org_id": org_id}
        )
        return bool(check)

    def verify_user_email_exists(self, email: str, org_id: int, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email already exists in organization."""
        exclude_clause = "AND user_id != %(exclude_user_id)s" if exclude_user_id else ""
        query = permission_query("VERIFY_USER_EMAIL_EXISTS").format(exclude_clause=exclude_clause)
        
        params = {"email": email, "org_id": org_id}
        if exclude_user_id:
            params["exclude_user_id"] = exclude_user_id
            
        check = self.db.fetch_one(query, params)
        return bool(check)

    # ======================================================
    # USER DATA VALIDATION
    # ======================================================

    def validate_user_data(self, user_data: Dict[str, Any], is_create: bool = False) -> Dict[str, Any]:
        validated = {}
        
        # For create, validate required fields
        if is_create:
            if not user_data.get("email"):
                raise AppException("Email is required", "MISSING_EMAIL", status_code=400)
            if not user_data.get("display_name"):
                raise AppException("Display name is required", "MISSING_DISPLAY_NAME", status_code=400)
        
        # Validate email
        email = user_data.get("email")
        if email is not None:
            email = email.strip().lower()
            if not email or "@" not in email:
                raise AppException("Invalid email format", "INVALID_EMAIL", status_code=400)
            validated["email"] = email
        
        # Validate display name
        display_name = user_data.get("display_name")
        if display_name is not None:
            display_name = display_name.strip()
            if not display_name:
                raise AppException("Display name cannot be empty", "EMPTY_DISPLAY_NAME", status_code=400)
            validated["display_name"] = display_name[:100]
        
        # Validate status
        status = user_data.get("status")
        if status:
            if status not in ['AC', 'IA', 'SU', 'EX', 'CA', 'DE']:
                raise AppException(f"Invalid status code: {status}", "INVALID_STATUS", status_code=400)
            validated["status"] = status
        elif is_create:
            validated["status"] = 'AC'
        
        # Validate dates
        status_effective_from = user_data.get("status_effective_from")
        status_effective_to = user_data.get("status_effective_to")
        
        if validated.get("status") == 'AC':
            if not status_effective_from:
                raise AppException("Active status requires an effective start date", "MISSING_START_DATE", status_code=400)
            if status_effective_to:
                raise AppException("Active status should not have an end date", "INVALID_END_DATE_FOR_ACTIVE", status_code=400)
        
        inactive_statuses = ['IA', 'SU', 'EX', 'CA', 'DE']
        if validated.get("status") in inactive_statuses and not status_effective_to:
            raise AppException(f"Status '{validated.get('status')}' requires an effective end date", "MISSING_END_DATE", status_code=400)
        
        if status_effective_from and status_effective_to:
            from_date = self._parse_date(status_effective_from)
            to_date = self._parse_date(status_effective_to)
            if to_date < from_date:
                raise AppException("End date cannot be before start date", "INVALID_DATE_RANGE", status_code=400)
        
        validated["status_effective_from"] = self._format_date_for_db(status_effective_from) if status_effective_from else None
        validated["status_effective_to"] = self._format_date_for_db(status_effective_to) if status_effective_to else None
        
        department = user_data.get("department")
        validated["department"] = str(department).strip()[:100] if department else None
        
        location = user_data.get("location")
        validated["location"] = str(location).strip()[:100] if location else None
        
        roles = user_data.get("roles")
        if roles is not None:
            if not isinstance(roles, list):
                raise AppException("Roles must be a list", "INVALID_ROLES_FORMAT", status_code=400)
            validated["roles"] = [str(role_id) for role_id in roles]
        
        return validated

    def _parse_date(self, date_str: str) -> date:
        try:
            if isinstance(date_str, str):
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            elif isinstance(date_str, datetime):
                return date_str.date()
            elif isinstance(date_str, date):
                return date_str
            else:
                raise ValueError(f"Cannot parse date: {date_str}")
        except (ValueError, AttributeError) as e:
            raise AppException(f"Invalid date format: {date_str}", "INVALID_DATE_FORMAT", status_code=400)

    def _format_date_for_db(self, date_value) -> Optional[str]:
        if date_value is None:
            return None
        try:
            if isinstance(date_value, str):
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return dt.isoformat()
            elif isinstance(date_value, datetime):
                return date_value.isoformat()
            elif isinstance(date_value, date):
                return datetime.combine(date_value, datetime.min.time()).isoformat()
            else:
                raise ValueError()
        except ValueError:
            raise AppException(f"Invalid date format: {date_value}", "INVALID_DATE_FORMAT", status_code=400)

    # ======================================================
    # USER GET OPERATIONS
    # ======================================================

    async def get_organization_users(self, current_user_id: int, offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        try:
            result = self.db.fetch_one_async(
                permission_query("ORGANIZATION_USERS_QUERY"),
                {"current_user_id": current_user_id, "offset": offset, "limit": limit}
            )
            if not result:
                raise AppException("No users found for your organization", "ORG_USERS_NOT_FOUND", status_code=404)

            return {
                "data": result['users_data'],
                "operation_metadata": {
                    "success": True,
                    "entity": "users",
                    "operation": "get",
                    "message": "Users fetched successfully",
                    "count": len(result['users_data']['items']),
                    "ids": [str(user['user_id']) for user in result['users_data'].get('items', [])]
                }
            }
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error fetching organization users: {e}")
            raise AppException("Failed to fetch users", "USER_FETCH_ERROR", status_code=500)

    def get_user_details(self, user_id: int, requesting_user_id: int) -> Dict[str, Any]:
        try:
            org_id, _ = self.get_user_organization(requesting_user_id)
            if not self.verify_user_access(user_id, org_id):
                raise AppException("User not found or access denied", "USER_ACCESS_DENIED", status_code=404)

            user_details = self.db.fetch_one(
                permission_query("GET_USER_DETAILS"),
                {"user_id": user_id, "org_id": org_id}
            )
            if not user_details:
                raise AppException("User details not found", "USER_NOT_FOUND", status_code=404)

            if user_details.get("status_effective_from"):
                user_details["status_effective_from"] = user_details["status_effective_from"].isoformat()
            if user_details.get("status_effective_to"):
                user_details["status_effective_to"] = user_details["status_effective_to"].isoformat()

            return {
                "data": user_details,
                "operation_metadata": {
                    "success": True,
                    "entity": "user",
                    "operation": "get",
                    "message": "User details fetched successfully",
                    "performed_by": requesting_user_id
                }
            }
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error fetching user details: {e}")
            raise AppException("Failed to fetch user details", "USER_DETAILS_ERROR", status_code=500)

    def search_users(self, org_id: int, search_term: str, offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        try:
            search_pattern = f"%{search_term}%"
            count_result = self.db.fetch_one(
                permission_query("SEARCH_USERS_COUNT"),
                {"org_id": org_id, "search_pattern": search_pattern}
            )
            users = self.db.fetch_all(
                permission_query("SEARCH_USERS"),
                {"org_id": org_id, "search_pattern": search_pattern, "offset": offset, "limit": limit}
            )

            return {
                "data": {
                    "items": users,
                    "total": count_result["total"] if count_result else 0,
                    "offset": offset,
                    "limit": limit,
                    "search_term": search_term
                },
                "operation_metadata": {
                    "success": True,
                    "entity": "users",
                    "operation": "search",
                    "message": f"Found {len(users)} users matching '{search_term}'",
                    "count": len(users)
                }
            }
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            raise AppException("Failed to search users", "USER_SEARCH_ERROR", status_code=500)

    # ======================================================
    # USER CREATE / UPDATE / DELETE OPERATIONS
    # ======================================================

    # --- bulk_create_users, bulk_update_users, bulk_delete_users ---
    # All raise AppException with correct status_code (400, 404, 409, 500) per scenario
    # Update user roles/fields methods also raise AppException with status_code

    # (Due to size constraints, I can provide the fully refactored bulk_create/update/delete
    # section next, including all appropriate status codes.)

    # ======================================================
    # USER CREATE OPERATIONS
    # ======================================================
    async def bulk_create_users(
        self,
        org_id: int,
        users_data: List[Dict[str, Any]],
        created_by: int | str
    ) -> Dict[str, Any]:

        created_ids = []

        for i, user_data in enumerate(users_data):
            try:
                # --------------------------
                # Required fields
                # --------------------------
                if not user_data.get("email"):
                    raise AppException(
                        message=f"Missing email at index {i}",
                        code="MISSING_EMAIL",
                        status_code=400
                    )
                if not user_data.get("display_name"):
                    raise AppException(
                        message=f"Missing display_name at index {i}",
                        code="MISSING_DISPLAY_NAME",
                        status_code=400
                    )

                # --------------------------
                # Validate user data
                # --------------------------
                validated_data = self.validate_user_data(user_data, is_create=True)

                # --------------------------
                # Check duplicate email
                # --------------------------
                if await self.verify_user_email_exists_async(validated_data["email"], org_id):
                    raise AppException(
                        message=f"Email '{validated_data['email']}' already exists in organization",
                        code="EMAIL_ALREADY_EXISTS",
                        status_code=409
                    )

                # --------------------------
                # Insert user (async)
                # --------------------------
                new_user = await self.db.execute_returning_async(
                    permission_query("INSERT_USER"),
                    {
                        "uid": validated_data["uid"],  # ✅ use UID from /register
                        "email": validated_data["email"],
                        "display_name": validated_data["display_name"],
                        "org_id": org_id,
                        "department": validated_data.get("department"),
                        "location": validated_data.get("location"),
                        "status": validated_data.get("status", "AC"),
                        "status_effective_from": validated_data.get("status_effective_from"),
                        "status_effective_to": validated_data.get("status_effective_to"),
                        "email_verified": validated_data["email_verified"],  # ✅ use real value
                    }
                )

                user_id = new_user["user_id"]
                created_ids.append(user_id)

                # --------------------------
                # Assign roles
                # --------------------------
                if "roles" in validated_data:
                    await self._update_user_roles_async(
                        user_id, org_id, validated_data["roles"], created_by
                    )

            except AppException:
                raise
            except Exception as e:
                logger.error(f"Unexpected error creating user at index {i}: {e}")
                raise AppException(
                    message=f"Failed to create user at index {i}: {str(e)}",
                    code="USER_CREATE_ERROR",
                    status_code=500
                )

        return {
            "success": True,
            "entity": "users",
            "operation": "create",
            "count": len(created_ids),
            "ids": created_ids,
            "message": f"Successfully created {len(created_ids)} users"
        }


    # ======================================================
    # USER UPDATE OPERATIONS
    # ======================================================

    def bulk_update_users(
        self,
        org_id: int,
        users_data: List[Dict[str, Any]],
        updated_by: int
    ) -> Dict[str, Any]:
        updated_ids = []
        roles_updated = 0
        fields_updated = 0

        with self.db.transaction():
            for i, user_data in enumerate(users_data):
                try:
                    user_id = user_data.get("user_id")
                    if not user_id:
                        raise AppException(
                            message=f"Missing user_id at index {i}",
                            code="MISSING_USER_ID",
                            status_code=400
                        )

                    if not self.verify_user_access(user_id, org_id):
                        raise AppException(
                            message=f"User {user_id} not found or access denied",
                            code="USER_ACCESS_DENIED",
                            status_code=404
                        )

                    validated_data = self.validate_user_data(user_data)

                    if "email" in validated_data:
                        if self.verify_user_email_exists(validated_data["email"], org_id, exclude_user_id=user_id):
                            raise AppException(
                                message=f"Email '{validated_data['email']}' already exists in organization",
                                code="EMAIL_ALREADY_EXISTS",
                                status_code=409
                            )

                    if i == 0 or len(users_data) == 1:
                        fields_updated += self._update_user_fields(
                            user_id, org_id, validated_data, updated_by
                        )

                    if "roles" in validated_data:
                        self._update_user_roles(
                            user_id, org_id, validated_data["roles"], updated_by
                        )
                        roles_updated += 1

                    updated_ids.append(user_id)

                except AppException:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error updating user at index {i}: {e}")
                    raise AppException(
                        message=f"Failed to update user at index {i}: {str(e)}",
                        code="USER_UPDATE_ERROR",
                        status_code=500
                    )

        return {
            "success": True,
            "entity": "users",
            "operation": "update",
            "count": len(updated_ids),
            "ids": [str(user_id) for user_id in updated_ids],
            "message": f"Successfully updated {len(updated_ids)} users",
            "details": {
                "roles_updated": roles_updated,
                "fields_updated": fields_updated,
                "bulk_mode": len(users_data) > 1
            }
        }


    def _update_user_fields(
        self,
        user_id: int,
        org_id: int,
        validated_data: Dict[str, Any],
        updated_by: int
    ) -> int:
        fields_to_update = {}
        field_mapping = {
            "email": "email",
            "display_name": "display_name",
            "department": "department",
            "location": "location",
            "status": "status",
            "status_effective_from": "status_effective_from",
            "status_effective_to": "status_effective_to"
        }

        for data_key, db_field in field_mapping.items():
            if data_key in validated_data:
                fields_to_update[db_field] = validated_data[data_key]

        if not fields_to_update:
            logger.info(f"No fields to update for user {user_id}")
            return 0

        set_clauses = []
        params = {"user_id": user_id, "org_id": org_id}
        for field, value in fields_to_update.items():
            if value is None:
                set_clauses.append(f"{field} = NULL")
            else:
                set_clauses.append(f"{field} = %({field})s")
                params[field] = value

        query = permission_query("UPDATE_USER_FIELDS").format(update_fields=", ".join(set_clauses))

        try:
            result = self.db.execute_returning(query, params)
            return 1 if result else 0
        except Exception as e:
            logger.error(f"Error updating user fields for user {user_id}: {e}")
            raise AppException(
                message=f"Failed to update fields for user {user_id}: {str(e)}",
                code="USER_FIELDS_UPDATE_ERROR",
                status_code=500
            )


    def _update_user_roles(
        self,
        user_id: int,
        org_id: int,
        role_ids: List[str],
        updated_by: int
    ):
        self.db.execute(
            permission_query("DELETE_USER_ROLES"),
            {"user_id": user_id, "org_id": org_id}
        )

        for role_id in role_ids:
            role_check = self.db.fetch_one(
                permission_query("VERIFY_ROLE_ACCESS"),
                {"role_id": int(role_id), "org_id": org_id}
            )
            if not role_check:
                raise AppException(
                    message=f"Role {role_id} not found or not accessible",
                    code="ROLE_ACCESS_DENIED",
                    status_code=404
                )

            try:
                self.db.execute(
                    permission_query("INSERT_USER_ROLE"),
                    {
                        "user_id": user_id,
                        "role_id": int(role_id),
                        "org_id": org_id,
                        "assigned_by": updated_by
                    }
                )
            except Exception as e:
                logger.error(f"Error assigning role {role_id} to user {user_id}: {e}")
                raise AppException(
                    message=f"Failed to assign role {role_id} to user {user_id}: {str(e)}",
                    code="USER_ROLE_ASSIGN_ERROR",
                    status_code=500
                )


    # ======================================================
    # USER DELETE OPERATIONS
    # ======================================================

    def bulk_delete_users(
        self,
        org_id: int,
        user_ids: List[int],
        deleted_by: int,
        hard_delete: bool = False
    ) -> Dict[str, Any]:
        deleted_count = 0
        deleted_user_ids = []

        with self.db.transaction():
            for user_id in user_ids:
                try:
                    if not self.verify_user_access(user_id, org_id):
                        raise AppException(
                            message=f"User {user_id} not found or access denied",
                            code="USER_ACCESS_DENIED",
                            status_code=404
                        )

                    query_type = "HARD_DELETE_USER" if hard_delete else "SOFT_DELETE_USER"
                    result = self.db.execute_returning(
                        permission_query(query_type),
                        {"user_id": user_id, "org_id": org_id}
                    )

                    if not result:
                        raise AppException(
                            message=f"Failed to delete user {user_id}",
                            code="USER_DELETE_FAILED",
                            status_code=409
                        )
                    
                    user_role_update = self.db.execute_returning(
                        permission_query("UPDATE_FOR_DELETE_USER"),
                        {"user_id": user_id, "org_id": org_id}
                    )
                    if not user_role_update:
                        raise AppException(
                            message=f"User {user_id} not found or not accessible",
                            code="USER_ROLE_ACCESS_DENIED",
                            status_code=404
                        )

                    deleted_count += 1
                    deleted_user_ids.append(user_id)

                except AppException:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error deleting user {user_id}: {e}")
                    raise AppException(
                        message=f"Failed to delete user {user_id}: {str(e)}",
                        code="USER_DELETE_ERROR",
                        status_code=500
                    )

        return {
            "success": True,
            "entity": "users",
            "operation": "delete",
            "count": deleted_count,
            "ids": [str(user_id) for user_id in deleted_user_ids],
            "message": f"Successfully deleted {deleted_count} users"
        }

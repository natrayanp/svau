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
            raise AppException("User organization not found", "ORG_NOT_FOUND")

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
        """
        Validate user data before saving.
        Returns validated and formatted data.
        """
        validated = {}
        
        # For create, validate required fields
        if is_create:
            if not user_data.get("email"):
                raise AppException("Email is required", "MISSING_EMAIL")
            if not user_data.get("display_name"):
                raise AppException("Display name is required", "MISSING_DISPLAY_NAME")
        
        # Validate email
        email = user_data.get("email")
        if email is not None:
            email = email.strip().lower()
            if not email or "@" not in email:
                raise AppException("Invalid email format", "INVALID_EMAIL")
            validated["email"] = email
        
        # Validate display name
        display_name = user_data.get("display_name")
        if display_name is not None:
            display_name = display_name.strip()
            if not display_name:
                raise AppException("Display name cannot be empty", "EMPTY_DISPLAY_NAME")
            validated["display_name"] = display_name[:100]
        
        # Validate status
        status = user_data.get("status")
        if status:
            if status not in ['AC', 'IA', 'SU', 'EX', 'CA', 'DE']:
                raise AppException(
                    f"Invalid status code: {status}",
                    "INVALID_STATUS"
                )
            validated["status"] = status
        elif is_create:
            # Default to Active for new users
            validated["status"] = 'AC'
        
        # Validate dates
        status_effective_from = user_data.get("status_effective_from")
        status_effective_to = user_data.get("status_effective_to")
        
        # Active status requires start date, no end date
        if validated.get("status") == 'AC':
            if not status_effective_from:
                raise AppException(
                    "Active status requires an effective start date",
                    "MISSING_START_DATE"
                )
            if status_effective_to:
                raise AppException(
                    "Active status should not have an end date",
                    "INVALID_END_DATE_FOR_ACTIVE"
                )
        
        # Inactive statuses require end date, start date optional
        inactive_statuses = ['IA', 'SU', 'EX', 'CA', 'DE']
        if validated.get("status") in inactive_statuses and not status_effective_to:
            raise AppException(
                f"Status '{validated.get('status')}' requires an effective end date",
                "MISSING_END_DATE"
            )
        
        # Date validation
        if status_effective_from and status_effective_to:
            from_date = self._parse_date(status_effective_from)
            to_date = self._parse_date(status_effective_to)
            
            if to_date < from_date:
                raise AppException(
                    "End date cannot be before start date",
                    "INVALID_DATE_RANGE"
                )
        
        # Format dates for database
        if status_effective_from:
            validated["status_effective_from"] = self._format_date_for_db(status_effective_from)
        else:
            validated["status_effective_from"] = None
        
        if status_effective_to:
            validated["status_effective_to"] = self._format_date_for_db(status_effective_to)
        else:
            validated["status_effective_to"] = None
        
        # Additional fields
        department = user_data.get("department")
        if department is not None:
            validated["department"] = str(department).strip()[:100] if department else None
        
        location = user_data.get("location")
        if location is not None:
            validated["location"] = str(location).strip()[:100] if location else None
        
        # Roles validation
        roles = user_data.get("roles")
        if roles is not None:
            if not isinstance(roles, list):
                raise AppException("Roles must be a list", "INVALID_ROLES_FORMAT")
            validated["roles"] = [str(role_id) for role_id in roles]
        
        return validated

    def _parse_date(self, date_str: str) -> date:
        """Parse date string to date object."""
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
            raise AppException(f"Invalid date format: {date_str}", "INVALID_DATE_FORMAT")

    def _format_date_for_db(self, date_value) -> Optional[str]:
        """Format date for database storage."""
        if date_value is None:
            return None
            
        if isinstance(date_value, str):
            # If it's already a string, ensure it's in ISO format
            try:
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return dt.isoformat()
            except ValueError:
                raise AppException(f"Invalid date format: {date_value}", "INVALID_DATE_FORMAT")
        elif isinstance(date_value, datetime):
            return date_value.isoformat()
        elif isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time()).isoformat()
        else:
            raise AppException(f"Unsupported date type: {type(date_value)}", "INVALID_DATE_TYPE")

    # ======================================================
    # USER GET OPERATIONS
    # ======================================================

    def get_organization_users(self, current_user_id: int, offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Get paginated users for the current user's organization."""
        try:
            result = self.db.fetch_one(
                permission_query("ORGANIZATION_USERS_QUERY"),
                {"current_user_id": current_user_id, "offset": offset, "limit": limit}
            )

            if not result:
                raise AppException(
                    message="No users found for your organization",
                    code="ORG_USERS_NOT_FOUND"
                )

            # Extract user IDs from the response
            users_data = result['users_data']
            user_ids = [str(user['user_id']) for user in users_data.get('items', [])]


            return {
                "data": result['users_data'],
                "operation_metadata": {
                    "success": True,
                    "entity": "users",
                    "operation": "get",
                    "message": "Users fetched successfully",
                    "count": len(result['users_data']['items']),
                    "ids": ['1']
                }
            }

        except Exception as e:
            logger.error(f"Error fetching organization users: {e}")
            raise

    def get_user_details(self, user_id: int, requesting_user_id: int) -> Dict[str, Any]:
        """Get detailed information for a single user with all fields."""
        try:
            # Get user's organization first
            org_id, _ = self.get_user_organization(requesting_user_id)
            
            # Verify the target user belongs to the same organization
            if not self.verify_user_access(user_id, org_id):
                raise AppException(
                    message="User not found or access denied",
                    code="USER_ACCESS_DENIED"
                )
            
            # Get user details with all fields
            user_details = self.db.fetch_one(
                permission_query("GET_USER_DETAILS"),
                {"user_id": user_id, "org_id": org_id}
            )

            if not user_details:
                raise AppException(
                    message="User details not found",
                    code="USER_NOT_FOUND"
                )

            # Format dates for response
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
            raise AppException(
                message="Failed to fetch user details",
                code="USER_DETAILS_ERROR"
            )

    def search_users(self, org_id: int, search_term: str, offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Search users by name, email, or UID within organization."""
        try:
            search_pattern = f"%{search_term}%"
            
            # First get total count
            count_result = self.db.fetch_one(
                permission_query("SEARCH_USERS_COUNT"),
                {"org_id": org_id, "search_pattern": search_pattern}
            )

            # Get paginated results
            users = self.db.fetch_all(
                permission_query("SEARCH_USERS"),
                {
                    "org_id": org_id,
                    "search_pattern": search_pattern,
                    "offset": offset,
                    "limit": limit
                }
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
            raise AppException(
                message="Failed to search users",
                code="USER_SEARCH_ERROR"
            )

    # ======================================================
    # USER CREATE OPERATIONS
    # ======================================================

    def bulk_create_users(
        self,
        org_id: int,
        users_data: List[Dict[str, Any]],
        created_by: int
    ) ->Dict[str, Any]:
        """
        Bulk create multiple users in a single transaction.
        ALL creations succeed or NONE do (all-or-nothing).
        """
        created_ids = []

        # START TRANSACTION
        with self.db.transaction():
            for i, user_data in enumerate(users_data):
                try:
                    # Validate required fields
                    if not user_data.get("email"):
                        raise AppException(
                            message=f"Missing email at index {i}",
                            code="MISSING_EMAIL"
                        )

                    if not user_data.get("display_name"):
                        raise AppException(
                            message=f"Missing display_name at index {i}",
                            code="MISSING_DISPLAY_NAME"
                        )

                    # Validate and prepare data
                    validated_data = self.validate_user_data(user_data, is_create=True)

                    # Check if email already exists in organization
                    if self.verify_user_email_exists(validated_data["email"], org_id):
                        raise AppException(
                            message=f"Email '{validated_data['email']}' already exists in organization",
                            code="EMAIL_ALREADY_EXISTS"
                        )

                    # Generate UID
                    import uuid
                    uid = str(uuid.uuid4())

                    # Create user
                    new_user = self.db.execute_returning(
                        """
                        INSERT INTO users (
                            uid,
                            email,
                            display_name,
                            org_id,
                            department,
                            location,
                            status,
                            status_effective_from,
                            status_effective_to,
                            email_verified,
                            created_at,
                            updated_at
                        ) VALUES (
                            %(uid)s,
                            %(email)s,
                            %(display_name)s,
                            %(org_id)s,
                            %(department)s,
                            %(location)s,
                            %(status)s,
                            %(status_effective_from)s,
                            %(status_effective_to)s,
                            FALSE,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                        RETURNING user_id
                        """,
                        {
                            "uid": uid,
                            "email": validated_data["email"],
                            "display_name": validated_data["display_name"],
                            "org_id": org_id,
                            "department": validated_data.get("department"),
                            "location": validated_data.get("location"),
                            "status": validated_data.get("status", "AC"),
                            "status_effective_from": validated_data.get("status_effective_from"),
                            "status_effective_to": validated_data.get("status_effective_to")
                        }
                    )

                    user_id = new_user["user_id"]
                    created_ids.append(user_id)

                    # Assign roles if provided
                    if "roles" in validated_data:
                        self._update_user_roles(
                            user_id, org_id, validated_data["roles"], created_by
                        )

                    # Log creation
                    """
                    self.db.execute(
                        
                        INSERT INTO permission_audit (user_id, action, performed_by, details)
                        VALUES (%(user_id)s, %(action)s, %(performed_by)s, %(details)s)
                        ,
                        {
                            "user_id": user_id,
                            "action": "CREATE_USER",
                            "performed_by": created_by,
                            "details": json.dumps({
                                "email": validated_data["email"],
                                "display_name": validated_data["display_name"],
                                "roles": validated_data.get("roles", []),
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        }
                    )
                    """

                except AppException:
                    # Re-raise to trigger transaction rollback
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error creating user at index {i}: {e}")
                    # Convert to AppException to trigger rollback
                    raise AppException(
                        message=f"Failed to create user at index {i}: {str(e)}",
                        code="USER_CREATE_ERROR"
                    )

        # If we reach here, transaction committed successfully
        return {
            "success": True,
            "entity": "users",
            "operation": "create",
            "count": len(created_ids),
            "ids": [str(user_id) for user_id in created_ids],
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
        """
        Bulk update multiple users in a single transaction.
        
        Updates can include:
        - Roles (replaces all existing roles)
        - Additional fields (department, location, status, dates)
        - For bulk updates, additional fields only update the first user
        
        Returns operation summary.
        """
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
                            code="MISSING_USER_ID"
                        )
                    
                    # Verify user belongs to organization
                    if not self.verify_user_access(user_id, org_id):
                        raise AppException(
                            message=f"User {user_id} not found or access denied",
                            code="USER_ACCESS_DENIED"
                        )
                    
                    # Validate and prepare data
                    validated_data = self.validate_user_data(user_data)
                    
                    # Check email uniqueness if email is being updated
                    if "email" in validated_data:
                        if self.verify_user_email_exists(validated_data["email"], org_id, exclude_user_id=user_id):
                            raise AppException(
                                message=f"Email '{validated_data['email']}' already exists in organization",
                                code="EMAIL_ALREADY_EXISTS"
                            )
                    
                    # Update user fields (only for first user in bulk mode, or all in single mode)
                    if i == 0 or len(users_data) == 1:
                        fields_updated += self._update_user_fields(
                            user_id, org_id, validated_data, updated_by
                        )
                    
                    # Update roles (always update for all users in bulk mode)
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
                        code="USER_UPDATE_ERROR"
                    )
        
        # Transaction committed successfully
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
        """Update user's additional fields."""
        fields_to_update = {}
        
        # Map validated data to database fields
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

        # DEBUG: Log what fields we're updating
        logger.info(f"Updating fields for user {user_id}: {fields_to_update}")

        # Build update query
        set_clauses = []
        params = {"user_id": user_id, "org_id": org_id}
        
        for field, value in fields_to_update.items():
            if value is None:
                set_clauses.append(f"{field} = NULL")  # Use NULL for None values
            else:
                set_clauses.append(f"{field} = %({field})s")
                params[field] = value
        
        query = permission_query("UPDATE_USER_FIELDS").format(update_fields=", ".join(set_clauses))
        # DEBUG: Log the query
        logger.info(f"Executing query: {query}")
        logger.info(f"With params: {params}")

        try:

            result = self.db.execute_returning(query, params)
            logger.info(f"Update result for user {user_id}: {result}")
        
            # Log update
            """if result:
                self.db.execute(
                    permission_query("LOG_USER_ACTION"),
                    {
                        "user_id": user_id,
                        "action": "UPDATE_USER_FIELDS",
                        "performed_by": updated_by,
                        "details": json.dumps({
                            "updated_fields": list(fields_to_update.keys()),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    }
                )
            """
            return 1 if result else 0
        
        except Exception as e:
            logger.error(f"Error updating user fields for user {user_id}: {e}")
            raise

    def _update_user_roles(
        self,
        user_id: int,
        org_id: int,
        role_ids: List[str],
        updated_by: int
    ):
        """Update user's roles (replaces all existing roles)."""
        # Delete existing roles
        self.db.execute(
            permission_query("DELETE_USER_ROLES"),
            {"user_id": user_id, "org_id": org_id}
        )
        
        # Insert new roles
        for role_id in role_ids:
            # Verify role belongs to organization
            role_check = self.db.fetch_one(
                permission_query("VERIFY_ROLE_ACCESS"),
                {"role_id": int(role_id), "org_id": org_id}
            )
            
            if not role_check:
                raise AppException(
                    message=f"Role {role_id} not found or not accessible",
                    code="ROLE_ACCESS_DENIED"
                )
            
            # Insert user role
            self.db.execute(
                permission_query("INSERT_USER_ROLE"),
                {
                    "user_id": user_id,
                    "role_id": int(role_id),
                    "org_id": org_id,
                    "assigned_by": updated_by
                }
            )
        
        # Log the role update
        """
        self.db.execute(
            permission_query("LOG_USER_ACTION"),
            {
                "user_id": user_id,
                "action": "UPDATE_ROLES",
                "performed_by": updated_by,
                "details": json.dumps({
                    "updated_roles": role_ids,
                    "organization_id": org_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
        )
        """

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
        """
        Bulk delete multiple users in a single transaction.
        ALL deletions succeed or NONE do (all-or-nothing).
        """
        deleted_count = 0
        deleted_user_ids = []

        # START TRANSACTION
        with self.db.transaction():
            for user_id in user_ids:
                try:
                    # Verify user belongs to organization
                    if not self.verify_user_access(user_id, org_id):
                        raise AppException(
                            message=f"User {user_id} not found or access denied",
                            code="USER_ACCESS_DENIED"
                        )

                    # Perform deletion
                    if hard_delete:
                        # Hard delete (permanently remove)
                        result = self.db.execute_returning(
                            permission_query("HARD_DELETE_USER"),
                            {
                                "user_id": user_id,
                                "org_id": org_id
                            }
                        )
                    else:
                        # Soft delete (mark as deleted)
                        result = self.db.execute_returning(
                            permission_query("SOFT_DELETE_USER"),
                            {
                                "user_id": user_id,
                                "org_id": org_id
                            }
                        )

                    if not result:
                        raise AppException(
                            message=f"Failed to delete user {user_id}",
                            code="USER_DELETE_FAILED"
                        )

                    deleted_count += 1
                    deleted_user_ids.append(user_id)

                    # Log deletion
                    """
                    self.db.execute(
                        
                        INSERT INTO permission_audit (user_id, action, performed_by, details)
                        VALUES (%(user_id)s, %(action)s, %(performed_by)s, %(details)s)
                        ,
                        {
                            "user_id": user_id,
                            "action": "HARD_DELETE_USER" if hard_delete else "SOFT_DELETE_USER",
                            "performed_by": deleted_by,
                            "details": json.dumps({
                                "user_id": user_id,
                                "hard_delete": hard_delete,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        }
                    )
                    """

                except AppException:
                    raise  # Trigger rollback
                except Exception as e:
                    logger.error(f"Unexpected error deleting user {user_id}: {e}")
                    raise AppException(
                        message=f"Failed to delete user {user_id}: {str(e)}",
                        code="USER_DELETE_ERROR"
                    )

        # If we reach here, transaction committed successfully
        return {
            "success": True,
            "entity": "users",
            "operation": "delete",
            "count": deleted_count,
            "ids": [str(user_id) for user_id in deleted_user_ids],
            "message": f"Successfully deleted {deleted_count} users",
        }

    # ======================================================
    # POWER ANALYSIS
    # ======================================================

    def get_user_power_analysis(self, user_id: int, requesting_user_id: int) -> Dict[str, Any]:
        """Get power analysis for a user based on assigned roles."""
        try:
            # Get user details with roles
            user_details = self.get_user_details(user_id, requesting_user_id)
            
            roles = user_details["data"].get("roles", [])
            if not roles:
                return {
                    "data": {
                        "user_id": user_id,
                        "permission_count": 0,
                        "max_power": 0,
                        "average_power": 0,
                        "power_distribution": {
                            "low": 0,
                            "medium": 0,
                            "high": 0,
                            "critical": 0
                        },
                        "most_powerful_permissions": [],
                        "analyzed_at": datetime.utcnow().isoformat()
                    },
                    "operation_metadata": {
                        "success": True,
                        "message": "User has no roles assigned"
                    }
                }
            
            # Get power levels for each role
            role_powers = []
            for role_id in roles:
                role_power = self.db.fetch_one(
                    permission_query("GET_ROLE_POWER_ANALYSIS"),
                    (int(role_id),)
                )
                if role_power:
                    role_powers.append(role_power)
            
            # Calculate analysis
            if not role_powers:
                max_power = 0
                total_permissions = 0
            else:
                max_power = max(rp["max_power"] for rp in role_powers)
                total_permissions = sum(rp["permission_count"] for rp in role_powers)
            
            # Power distribution
            if max_power >= 100:
                distribution = {"low": 0, "medium": 0, "high": 0, "critical": 1}
            elif max_power >= 80:
                distribution = {"low": 0, "medium": 0, "high": 1, "critical": 0}
            elif max_power >= 60:
                distribution = {"low": 0, "medium": 1, "high": 0, "critical": 0}
            else:
                distribution = {"low": 1, "medium": 0, "high": 0, "critical": 0}
            
            analysis_data = {
                "user_id": user_id,
                "permission_count": total_permissions,
                "max_power": max_power,
                "average_power": max_power,  # Simplified for now
                "power_distribution": distribution,
                "most_powerful_permissions": [
                    {
                        "permission_id": "system",
                        "display_name": "Highest Role Power",
                        "power_level": max_power
                    }
                ],
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return {
                "data": analysis_data,
                "operation_metadata": {
                    "success": True,
                    "entity": "user_power_analysis",
                    "operation": "get",
                    "message": f"Power analysis completed for user {user_id}"
                }
            }
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to analyze user permissions: {str(e)}")
            raise AppException(
                message=f"Failed to analyze user permissions: {str(e)}",
                code="POWER_ANALYSIS_ERROR"
            )
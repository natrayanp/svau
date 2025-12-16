import logging
from typing import Dict, Any, Optional, Union
from utils.database.database import DatabaseManager
from utils.database.query_manager import permission_query
from utils.appwide.errors import AppException
from routes.auth.services.role_service import RoleService
from models.permission_models import OrganizationInfo

logger = logging.getLogger(__name__)


class OrganizationService:
    """
    Async service for:
    - Creating organizations
    - Bootstrapping system roles
    - Fetching organization details
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.role_service = RoleService(db)

    # ======================================================
    # CREATE ORGANIZATION (ASYNC)
    # ======================================================

    async def create_organization(self, name: str, created_by: str) -> int:
        if not name or not name.strip():
            raise AppException("Organization name is required", "ORG_NAME_REQUIRED", 400)

        name = name.strip()
        slug = name.lower().replace(" ", "-")

        try:
            org = await self.db.execute_returning_async(
                permission_query("CREATE_ORGANIZATION"),
                (name, slug, "AC", created_by)
            )

            if not org or "org_id" not in org:
                raise AppException("Failed to create organization", "ORG_CREATE_FAILED", 500)

            org_id = org["org_id"]
            logger.info(f"Created organization '{name}' (ID: {org_id})")

            # Bootstrap system roles
            await self.bootstrap_system_roles(org_id, created_by)

            return org_id

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating organization: {e}")
            raise AppException("Unexpected error creating organization", "ORG_CREATE_ERROR", 500)

    # ======================================================
    # BOOTSTRAP SYSTEM ROLES (ASYNC)
    # ======================================================

    async def bootstrap_system_roles(self, org_id: int, created_by: str):
        try:
            await self.role_service.clone_system_roles_for_org_async(org_id, created_by)
            logger.info(f"Bootstrapped system roles for org {org_id}")
        except Exception as e:
            logger.error(f"Error bootstrapping system roles for org {org_id}: {e}")
            raise AppException("Failed to bootstrap system roles", "ORG_ROLE_BOOTSTRAP_FAILED", 500)

    # ======================================================
    # GET ORGANIZATION (ASYNC)
    # ======================================================

    async def get_organization_async(
        self,
        org_id: int,
        mode: str = "bool"
    ) -> Union[bool, Optional[int], Optional[OrganizationInfo]]:
        org = await self.db.fetch_one_async(
            permission_query("GET_ORGANIZATION_BY_ID"),
            (org_id,)
        )
        return self._format_org_result(org, mode)

    # ======================================================
    # INTERNAL FORMATTER
    # ======================================================

    def _format_org_result(
        self,
        org: Optional[Dict[str, Any]],
        mode: str
    ):
        if mode == "bool":
            return bool(org)

        if mode == "id":
            return org["org_id"] if org else None

        if mode == "full":
            return OrganizationInfo(**org) if org else None

        raise AppException(
            f"Invalid mode '{mode}' for get_organization",
            "INVALID_ORG_FETCH_MODE",
            400
        )

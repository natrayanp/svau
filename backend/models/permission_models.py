# models/api_models.py

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime

T = TypeVar('T')  # Generic type for success data
E = TypeVar('E')  # Generic type for error details

# ==================== GENERIC ID STRING MIXIN ====================

class IdStringMixin(BaseModel):
    """Mixin to convert integer IDs to strings automatically"""
    
    @staticmethod
    def convert_to_str(value: Any):
        if isinstance(value, int):
            return str(value)
        if isinstance(value, list):
            return [str(v) if isinstance(v, int) else v for v in value]
        return value


# ==================== PERMISSION STRUCTURE MODELS ====================

class ActionDetail(BaseModel):
    action_key: str
    display_name: str
    power_level: int
    category: Optional[str] = None

class PermissionDetail(IdStringMixin):
    id: str
    permission_action: str
    display_name: str
    description: str
    power_level: int
    default_roles: Optional[List[str]] = None
    icon: Optional[str] = None
    card_id: Optional[str] = None
    card_name: Optional[str] = None
    menu_name: Optional[str] = None
    module_name: Optional[str] = None

    _convert_id = validator("id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class CardDetail(IdStringMixin):
    id: str
    key: str
    name: str
    description: str
    display_order: int
    menu_id: str
    allowed_actions: Optional[List[ActionDetail]] = []

    _convert_id = validator("id", "menu_id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class MenuDetail(IdStringMixin):
    id: str
    key: str
    name: str
    description: str
    display_order: int
    module_id: str
    cards: List[CardDetail]
    allowed_actions: Optional[List[ActionDetail]] = []

    _convert_id = validator("id", "module_id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class ModuleDetail(IdStringMixin):
    id: str
    key: str
    name: str
    icon: str
    color: str
    description: str
    display_order: int
    menus: List[MenuDetail]
    allowed_actions: Optional[List[ActionDetail]] = []

    _convert_id = validator("id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class PermissionStructureMetadata(BaseModel):
    total_modules: int
    total_menus: int
    total_cards: int
    total_permissions: int
    last_updated: str

class PermissionStructure(BaseModel):
    modules: List[ModuleDetail]
    metadata: PermissionStructureMetadata

class PermissionStructureAPIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[PermissionStructure] = None

# ==================== ROLE AND PERMISSIONS ====================

class PermissionItem(IdStringMixin):
    permissstruct_id: str
    granted_action_key: List[str]

    _convert_id = validator("permissstruct_id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class Role(IdStringMixin):
    role_id: str
    display_name: str
    description: Optional[str] = None
    is_system_role: bool
    is_template: bool
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    permission_count: int
    permission_ids: List[PermissionItem]
    user_count: int
    created_at: datetime

    _convert_role_id = validator("role_id", "template_id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class RolesSummary(BaseModel):
    total_roles: int
    system_roles: int
    template_roles: int
    custom_roles: int
    total_permission_assignments: int
    total_user_assignments: int
    current_organization: int
    package_restrictions_applied: bool

class RoleModel(BaseModel):
    roles: List[Role]
    summary: RolesSummary

# ==================== USER MODELS ====================

class UserPermissionsResponse(IdStringMixin):
    user_id: str
    permission_ids: List[str]

    @validator("permission_ids", pre=True)
    def convert_permission_ids(cls, v):
        return [str(i) for i in v] if isinstance(v, list) else v

class PermissionValidationRequest(IdStringMixin):
    parent_permission_ids: List[str]
    child_permission_ids: List[str]

    _convert_ids = validator("parent_permission_ids", "child_permission_ids", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

class UserModel(IdStringMixin):
    user_id: str
    uid: str
    email: EmailStr
    display_name: Optional[str] = None
    org_id: int
    email_verified: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status_effective_from: Optional[datetime] = None
    status_effective_to: Optional[datetime] = None
    roles: List[str] = []

    _convert_ids = validator("user_id", "org_id", pre=True, allow_reuse=True)(IdStringMixin.convert_to_str)

    class Config:
        from_attributes = True

# ==================== HEALTH CHECK ====================

class HealthCheck(BaseModel):
    status: str
    services: Dict[str, bool]
    tables: Dict[str, bool]
    metrics: Dict[str, Any]
    last_updated: str



# ==================== ORGANIZATION MODELS ====================

class OrganizationInfo(BaseModel):
    org_id: int
    name: str
    slug: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

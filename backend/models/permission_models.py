from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== PERMISSION STRUCTURE MODELS ====================

class ActionDetail(BaseModel):
    action_key: str
    display_name: str
    power_level: int
    category: Optional[str] = None

class PermissionDetail(BaseModel):
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

class CardDetail(BaseModel):
    id: str
    key: str
    name: str
    description: str
    display_order: int
    menu_id: str
    #permissions: List[PermissionDetail]
    allowed_actions: Optional[List[ActionDetail]] = []  # From SQL query

class MenuDetail(BaseModel):
    id: str
    key: str
    name: str
    description: str
    display_order: int
    module_id: str
    #permissions: List[PermissionDetail]
    cards: List[CardDetail]
    allowed_actions: Optional[List[ActionDetail]] = []  # From SQL query

class ModuleDetail(BaseModel):
    id: str
    key: str
    name: str
    icon: str
    color: str
    description: str
    display_order: int
    menus: List[MenuDetail]
    allowed_actions: Optional[List[ActionDetail]] = []  # From SQL query

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

# ==================== UPDATE EXISTING MODELS ====================

# Update your existing UserPermissionsResponse to use string IDs
class UserPermissionsResponse(BaseModel):
    user_id: int
    permission_ids: List[str]  # ← Change from List[int] to List[str]

'''class RolePermissionsResponse(BaseModel):
    role: str
    permission_ids: List[str]  # ← Change from List[int] to List[str]
    permission_count: int



class RolePermissionsUpdateRequest(BaseModel):
    permission_ids: List[str]  # ← Change from List[int] to List[str]

class UserPermissionsRequest(BaseModel):
    permission_ids: List[str]  # ← Change from List[int] to List[str]
'''
class PermissionValidationRequest(BaseModel):
    parent_permission_ids: List[str]  # ← Change from List[int] to List[str]
    child_permission_ids: List[str]   # ← Change from List[int] to List[str]

# ==================== ADDITIONAL MODELS FOR OTHER ENDPOINTS ====================

class RoleTemplate(BaseModel):
    template_key: str
    template_name: str
    description: str
    permission_ids: List[str]
    power_level: int
    is_system_template: bool
    permission_details: Optional[List[Dict[str, Any]]] = None
    roles_using_count: int
    created_at: datetime
    updated_at: datetime

class PermissionItem(BaseModel):
    permissstruct_id: int = Field(..., description="Permission structure identifier")
    granted_action_key: List[str] = Field(..., description="List of granted actions")

class Role(BaseModel):
    role_id: str
    display_name: str
    description: Optional[str] = None
    is_system_role: bool
    is_template: bool
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    permission_count: int
    permission_ids: List[PermissionItem]   # IDs of granted permissions
    user_count: int
    created_at: datetime



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


class QuickAction(BaseModel):
    icon: str
    label: str
    href: str
    description: str

class HealthCheck(BaseModel):
    status: str
    services: Dict[str, bool]
    tables: Dict[str, bool]
    metrics: Dict[str, Any]
    last_updated: str


class UserModel(BaseModel):
    user_id: int
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

    class Config:
        from_attributes = True

    
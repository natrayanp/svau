from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    BASIC = "basic"
    CREATOR = "creator"
    MODERATOR = "moderator"
    ADMIN = "admin"

# POWER-BASED MODELS
class UserPermissionsRequest(BaseModel):
    permission_ids: List[int]

    @validator('permission_ids', each_item=True)
    def validate_permission_id(cls, v):
        if not isinstance(v, int) or v <= 0:
            raise ValueError('Permission ID must be a positive integer')
        return v

class UserPermissionsResponse(BaseModel):
    user_id: int
    permission_ids: List[int]

class PermissionValidationRequest(BaseModel):
    parent_permission_ids: List[int]
    child_permission_ids: List[int]

class PermissionValidationResponse(BaseModel):
    max_parent_power: int
    validation_results: List[Dict[str, Any]]
    all_allowed: bool

class AllowedPermissionsResponse(BaseModel):
    allowed_permissions: List[Dict[str, Any]]
    max_parent_power: int

class PowerAnalysisResponse(BaseModel):
    role: str
    permission_count: int
    max_power: int
    average_power: float
    power_distribution: Dict[str, int]
    most_powerful_permissions: List[Dict[str, Any]]

class RoleTemplate(BaseModel):
    name: str
    description: str
    permission_ids: List[int]
    power_level: int

class RolePermissionsResponse(BaseModel):
    role: str
    permission_ids: List[int]
    permission_count: int

# PERMISSION STRUCTURE MODELS
class PermissionDetail(BaseModel):
    id: int
    action: str
    display_name: str
    description: str
    power_level: int
    default_roles: List[str]

class CardDetail(BaseModel):
    id: int
    key: str
    name: str
    description: str
    display_order: int
    menu_id: int
    permissions: List[PermissionDetail]

class MenuDetail(BaseModel):
    id: int
    key: str
    name: str
    description: str
    display_order: int
    module_id: int
    cards: List[CardDetail]

class ModuleDetail(BaseModel):
    id: int
    key: str
    name: str
    icon: str
    color: str
    description: str
    display_order: int
    menus: List[MenuDetail]

class StructureMetadata(BaseModel):
    total_modules: int
    total_menus: int
    total_cards: int
    total_permissions: int
    last_updated: str

class PermissionStructureResponse(BaseModel):
    modules: List[ModuleDetail]
    metadata: StructureMetadata

class PermissionStructureAPIResponse(BaseModel):
    success: bool
    data: PermissionStructureResponse

# EXISTING USER MODELS (unchanged)
class UserBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    role: UserRole = UserRole.BASIC

class UserCreate(UserBase):
    uid: str
    email_verified: bool = False

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[UserRole] = None
    email_verified: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    uid: str
    email_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    firebase_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SuccessResponse(BaseModel):
    success: bool
    message: str

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

class PermissionAuditResponse(BaseModel):
    id: int
    user_id: int
    permission_id: int
    action: str
    performed_by: int
    performed_at: datetime

    class Config:
        from_attributes = True
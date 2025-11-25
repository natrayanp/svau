from typing import Set, List, Dict, Any
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from datetime import datetime
from .middleware import get_current_user
from backend.utils.database import get_db
from models.auth_models import User

# Define power levels for all actions
ACTION_POWER_LEVELS = {
    'view': 10,
    'analytics': 15,
    'export': 20,
    'create': 25,
    'edit': 30,
    'import': 35,
    'delete': 60,
    'manage': 80,
    'admin': 100
}

# Enhanced permission structure with power levels
PERMISSION_STRUCTURE = {
    "modules": [
        {
            "id": 1,
            "key": "flashcards",
            "name": "Flashcards",
            "icon": "📚",
            "color": "blue",
            "description": "Flashcard management system",
            "display_order": 1,
            "menus": [
                {
                    "id": 101,
                    "key": "dashboard",
                    "name": "Dashboard",
                    "description": "Overview and analytics",
                    "display_order": 1,
                    "module_id": 1,
                    "cards": [
                        {
                            "id": 1001,
                            "key": "overview",
                            "name": "Overview",
                            "description": "Main dashboard overview",
                            "display_order": 1,
                            "menu_id": 101,
                            "permissions": [
                                {
                                    "id": 5001,
                                    "action": "view",
                                    "display_name": "View",
                                    "description": "View overview dashboard",
                                    "power_level": 10,
                                    "default_roles": ["basic", "creator", "moderator", "admin"]
                                },
                                {
                                    "id": 5002,
                                    "action": "analytics",
                                    "display_name": "Analytics",
                                    "description": "Access analytics data",
                                    "power_level": 15,
                                    "default_roles": ["creator", "moderator", "admin"]
                                },
                                {
                                    "id": 5003,
                                    "action": "export",
                                    "display_name": "Export",
                                    "description": "Export dashboard data",
                                    "power_level": 20,
                                    "default_roles": ["creator", "moderator", "admin"]
                                }
                            ]
                        },
                        {
                            "id": 1002,
                            "key": "statistics",
                            "name": "Statistics",
                            "description": "Usage statistics and reports",
                            "display_order": 2,
                            "menu_id": 101,
                            "permissions": [
                                {
                                    "id": 5004,
                                    "action": "view",
                                    "display_name": "View",
                                    "description": "View statistics",
                                    "power_level": 10,
                                    "default_roles": ["basic", "creator", "moderator", "admin"]
                                },
                                {
                                    "id": 5005,
                                    "action": "export",
                                    "display_name": "Export",
                                    "description": "Export statistics data",
                                    "power_level": 20,
                                    "default_roles": ["creator", "moderator", "admin"]
                                }
                            ]
                        }
                    ]
                },
                {
                    "id": 102,
                    "key": "cards",
                    "name": "Cards",
                    "description": "Card management",
                    "display_order": 2,
                    "module_id": 1,
                    "cards": [
                        {
                            "id": 1003,
                            "key": "card_list",
                            "name": "Card List",
                            "description": "List and manage all cards",
                            "display_order": 1,
                            "menu_id": 102,
                            "permissions": [
                                {
                                    "id": 5006,
                                    "action": "view",
                                    "display_name": "View",
                                    "description": "View card list",
                                    "power_level": 10,
                                    "default_roles": ["basic", "creator", "moderator", "admin"]
                                },
                                {
                                    "id": 5007,
                                    "action": "create",
                                    "display_name": "Create",
                                    "description": "Create new cards",
                                    "power_level": 25,
                                    "default_roles": ["creator", "moderator", "admin"]
                                },
                                {
                                    "id": 5008,
                                    "action": "edit",
                                    "display_name": "Edit",
                                    "description": "Edit existing cards",
                                    "power_level": 30,
                                    "default_roles": ["creator", "moderator", "admin"]
                                },
                                {
                                    "id": 5009,
                                    "action": "delete",
                                    "display_name": "Delete",
                                    "description": "Delete cards",
                                    "power_level": 60,
                                    "default_roles": ["moderator", "admin"]
                                },
                                {
                                    "id": 5010,
                                    "action": "import",
                                    "display_name": "Import",
                                    "description": "Import cards",
                                    "power_level": 35,
                                    "default_roles": ["moderator", "admin"]
                                },
                                {
                                    "id": 5011,
                                    "action": "export",
                                    "display_name": "Export",
                                    "description": "Export cards",
                                    "power_level": 20,
                                    "default_roles": ["creator", "moderator", "admin"]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": 2,
            "key": "portfolio",
            "name": "Portfolio",
            "icon": "💼",
            "color": "green",
            "description": "Project portfolio management",
            "display_order": 2,
            "menus": [
                {
                    "id": 201,
                    "key": "projects",
                    "name": "Projects",
                    "description": "Project management",
                    "display_order": 1,
                    "module_id": 2,
                    "cards": [
                        {
                            "id": 2001,
                            "key": "project_list",
                            "name": "Project List",
                            "description": "List and manage projects",
                            "display_order": 1,
                            "menu_id": 201,
                            "permissions": [
                                {
                                    "id": 6001,
                                    "action": "view",
                                    "display_name": "View",
                                    "description": "View project list",
                                    "power_level": 10,
                                    "default_roles": ["basic", "creator", "moderator", "admin"]
                                },
                                {
                                    "id": 6002,
                                    "action": "create",
                                    "display_name": "Create",
                                    "description": "Create new projects",
                                    "power_level": 25,
                                    "default_roles": ["creator", "moderator", "admin"]
                                },
                                {
                                    "id": 6003,
                                    "action": "edit",
                                    "display_name": "Edit",
                                    "description": "Edit projects",
                                    "power_level": 30,
                                    "default_roles": ["creator", "moderator", "admin"]
                                },
                                {
                                    "id": 6004,
                                    "action": "delete",
                                    "display_name": "Delete",
                                    "description": "Delete projects",
                                    "power_level": 60,
                                    "default_roles": ["moderator", "admin"]
                                },
                                {
                                    "id": 6005,
                                    "action": "publish",
                                    "display_name": "Publish",
                                    "description": "Publish projects",
                                    "power_level": 40,
                                    "default_roles": ["creator", "moderator", "admin"]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": 3,
            "key": "users",
            "name": "Users",
            "icon": "👥",
            "color": "purple",
            "description": "User management system",
            "display_order": 3,
            "menus": [
                {
                    "id": 301,
                    "key": "user_management",
                    "name": "User Management",
                    "description": "Manage users and permissions",
                    "display_order": 1,
                    "module_id": 3,
                    "cards": [
                        {
                            "id": 3001,
                            "key": "user_list",
                            "name": "User List",
                            "description": "List and manage users",
                            "display_order": 1,
                            "menu_id": 301,
                            "permissions": [
                                {
                                    "id": 8001,
                                    "action": "view",
                                    "display_name": "View Users",
                                    "description": "View user list and profiles",
                                    "power_level": 70,
                                    "default_roles": ["moderator", "admin"]
                                },
                                {
                                    "id": 8002,
                                    "action": "manage",
                                    "display_name": "Manage Users",
                                    "description": "Manage user roles and permissions",
                                    "power_level": 80,
                                    "default_roles": ["admin"]
                                },
                                {
                                    "id": 8003,
                                    "action": "admin",
                                    "display_name": "Admin Access",
                                    "description": "Full administrative access",
                                    "power_level": 90,
                                    "default_roles": ["admin"]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": 4,
            "key": "admin",
            "name": "Admin",
            "icon": "⚙️",
            "color": "orange",
            "description": "Administration panel",
            "display_order": 4,
            "menus": [
                {
                    "id": 401,
                    "key": "system",
                    "name": "System",
                    "description": "System administration",
                    "display_order": 1,
                    "module_id": 4,
                    "cards": [
                        {
                            "id": 4001,
                            "key": "system_settings",
                            "name": "System Settings",
                            "description": "Manage system settings",
                            "display_order": 1,
                            "menu_id": 401,
                            "permissions": [
                                {
                                    "id": 9001,
                                    "action": "access",
                                    "display_name": "Admin Access",
                                    "description": "Access administration panel",
                                    "power_level": 100,
                                    "default_roles": ["admin"]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

# Create permission ID mapping
PERMISSION_ID_MAP = {}
for module in PERMISSION_STRUCTURE["modules"]:
    for menu in module["menus"]:
        for card in menu["cards"]:
            for permission in card["permissions"]:
                PERMISSION_ID_MAP[permission["id"]] = permission

class ExplicitPermissionSystem:
    @lru_cache(maxsize=128)
    def get_user_permission_ids(self, user_id: int) -> Set[int]:
        """Get user's direct permission IDs"""
        db = next(get_db())
        try:
            permissions = db.execute_query(
                "SELECT permission_id FROM user_permissions WHERE user_id = %s",
                (user_id,),
                fetch=True
            )
            return {row['permission_id'] for row in permissions}
        finally:
            db.close()

    def get_user_permission_ids_with_roles(self, user_id: int, db) -> Set[int]:
        """Get combined permission IDs from user and roles"""
        user_permissions = self.get_user_permission_ids(user_id)
        
        user_data = db.execute_query(
            "SELECT role FROM users WHERE id = %s",
            (user_id,),
            fetch=True
        )
        
        if not user_data:
            return user_permissions
            
        user_role = user_data[0]['role']
        role_permissions = RolePermissions.get_permission_ids_for_role(user_role)
        
        return user_permissions.union(role_permissions)

    def check_permission_by_id(self, user_permission_ids: Set[int], permission_id: int) -> bool:
        """Direct ID-based permission check"""
        return permission_id in user_permission_ids

    def get_permission_details(self, permission_id: int) -> Dict[str, Any]:
        """Get permission details by ID"""
        return PERMISSION_ID_MAP.get(permission_id)

    def get_permission_power(self, permission_id: int) -> int:
        """Get power level of a permission"""
        perm_details = self.get_permission_details(permission_id)
        return perm_details.get("power_level", 0) if perm_details else 0

    def get_max_power_from_permissions(self, permission_ids: List[int]) -> int:
        """Get maximum power level from a list of permission IDs"""
        if not permission_ids:
            return 0
        
        max_power = 0
        for perm_id in permission_ids:
            power = self.get_permission_power(perm_id)
            max_power = max(max_power, power)
        
        return max_power

    def get_allowed_child_permissions(self, parent_permission_ids: List[int]) -> List[Dict[str, Any]]:
        """Get permissions that children can have based on parent's max power"""
        max_parent_power = self.get_max_power_from_permissions(parent_permission_ids)
        
        allowed_permissions = []
        for module in PERMISSION_STRUCTURE["modules"]:
            for menu in module["menus"]:
                for card in menu["cards"]:
                    for permission in card["permissions"]:
                        if permission["power_level"] <= max_parent_power:
                            allowed_permissions.append(permission)
        
        return allowed_permissions

    def validate_child_permissions(self, parent_permission_ids: List[int], child_permission_ids: List[int]) -> Dict[str, Any]:
        """Validate if child permissions are allowed by parent constraints"""
        max_parent_power = self.get_max_power_from_permissions(parent_permission_ids)
        
        validation_results = []
        all_allowed = True
        
        for child_perm_id in child_permission_ids:
            child_perm = self.get_permission_details(child_perm_id)
            if child_perm:
                is_allowed = child_perm["power_level"] <= max_parent_power
                validation_results.append({
                    "permission_id": child_perm_id,
                    "permission_name": child_perm["display_name"],
                    "power_level": child_perm["power_level"],
                    "is_allowed": is_allowed,
                    "reason": "Allowed" if is_allowed else f"Power level {child_perm['power_level']} exceeds parent max {max_parent_power}"
                })
                if not is_allowed:
                    all_allowed = False
        
        return {
            "max_parent_power": max_parent_power,
            "validation_results": validation_results,
            "all_allowed": all_allowed
        }

    def get_user_max_power(self, user_id: int, db) -> int:
        """Get the maximum power level a user has across all permissions"""
        user_permission_ids = self.get_user_permission_ids_with_roles(user_id, db)
        return self.get_max_power_from_permissions(list(user_permission_ids))

    def can_user_access_power_level(self, user_id: int, required_power: int, db) -> bool:
        """Check if user has permissions with sufficient power level"""
        user_max_power = self.get_user_max_power(user_id, db)
        return user_max_power >= required_power

    def get_default_permissions_for_new_module(self) -> List[int]:
        """Get default permissions for a new module (least powerful)"""
        default_permissions = []
        for module in PERMISSION_STRUCTURE["modules"]:
            for menu in module["menus"]:
                for card in menu["cards"]:
                    for permission in card["permissions"]:
                        if permission["power_level"] == 10:  # Least powerful
                            default_permissions.append(permission["id"])
        return default_permissions[:1]  # Return just one least powerful permission

    def get_permissions_following_parent(self, parent_permission_ids: List[int], available_permission_ids: List[int]) -> List[int]:
        """Get permissions that follow parent's permissions within constraints"""
        max_parent_power = self.get_max_power_from_permissions(parent_permission_ids)
        
        following_permissions = []
        for perm_id in available_permission_ids:
            perm_power = self.get_permission_power(perm_id)
            if perm_power <= max_parent_power:
                following_permissions.append(perm_id)
        
        return following_permissions

class RolePermissions:
    @staticmethod
    def get_permission_ids_for_role(role: str) -> Set[int]:
        """Role permissions as IDs with power levels"""
        role_permission_ids = {
            "basic": {
                5001,  # flashcards.dashboard.overview.view (10)
                5004,  # flashcards.dashboard.statistics.view (10)
                6001,  # portfolio.projects.project_list.view (10)
                7001   # user.profile.view (10) - hypothetical
            },
            "creator": {
                5001, 5002, 5003,  # flashcards.dashboard.* (10,15,20)
                5004, 5005,        # flashcards.dashboard.statistics.* (10,20)
                5006, 5007, 5008,  # flashcards.cards.card_list.* (10,25,30)
                6001, 6002, 6003,  # portfolio.projects.project_list.* (10,25,30)
                7001, 7002         # user.profile.* (10,30) - hypothetical
            },
            "moderator": {
                5001, 5002, 5003, 5004, 5005,  # flashcards.dashboard.*
                5006, 5007, 5008, 5009,        # flashcards.cards.card_list.*
                6001, 6002, 6003, 6004,        # portfolio.projects.project_list.*
                8001, 8002,                    # users.* (70,80)
                7001, 7002                     # user.profile.*
            },
            "admin": {
                5001, 5002, 5003, 5004, 5005,  # flashcards.dashboard.*
                5006, 5007, 5008, 5009, 5010, 5011,  # flashcards.cards.card_list.*
                6001, 6002, 6003, 6004, 6005,  # portfolio.projects.project_list.*
                8001, 8002, 8003,              # users.* (70,80,90)
                9001,                          # admin.access (100)
                7001, 7002                     # user.profile.*
            }
        }
        return role_permission_ids.get(role, set())

    @staticmethod
    def get_role_power_analysis(role: str) -> Dict[str, Any]:
        """Get power analysis for a role"""
        perm_system = ExplicitPermissionSystem()
        role_permissions = RolePermissions.get_permission_ids_for_role(role)
        
        permission_details = []
        total_power = 0
        max_power = 0
        
        for perm_id in role_permissions:
            perm_details = perm_system.get_permission_details(perm_id)
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
        
        return {
            "role": role,
            "permission_count": len(permission_details),
            "max_power": max_power,
            "average_power": round(avg_power, 2),
            "power_distribution": power_distribution,
            "most_powerful_permissions": [
                p for p in permission_details if p["power_level"] == max_power
            ]
        }

    @staticmethod
    def find_permission_conflicts(role_permissions: Dict[str, Set[int]]) -> List[Dict[str, Any]]:
        """Find permission conflicts between roles"""
        conflicts = []
        roles = list(role_permissions.keys())
        
        for i, role1 in enumerate(roles):
            for role2 in roles[i+1:]:
                perms1 = role_permissions[role1]
                perms2 = role_permissions[role2]
                
                # Find common permissions
                common_perms = perms1.intersection(perms2)
                
                for perm_id in common_perms:
                    perm_details = ExplicitPermissionSystem().get_permission_details(perm_id)
                    if perm_details:
                        conflicts.append({
                            'type': 'DUPLICATE_PERMISSION',
                            'permission_id': perm_id,
                            'permission_name': perm_details['display_name'],
                            'roles': [role1, role2],
                            'severity': 'LOW',
                            'message': f'Permission "{perm_details["display_name"]}" exists in both {role1} and {role2}'
                        })
        
        return conflicts

# POWER-BASED DEPENDENCIES
def require_permission_id(permission_id: int):
    """ID-based permission dependency"""
    async def permission_dependency(
        user: User = Depends(get_current_user),
        db = Depends(get_db)
    ):
        perm_system = ExplicitPermissionSystem()
        user_permission_ids = perm_system.get_user_permission_ids_with_roles(user.id, db)
        
        if not perm_system.check_permission_by_id(user_permission_ids, permission_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_id}"
            )
        return user
    return permission_dependency

def require_minimum_power(required_power: int):
    """Dependency to require minimum power level"""
    async def power_dependency(
        user: User = Depends(get_current_user),
        db = Depends(get_db)
    ):
        perm_system = ExplicitPermissionSystem()
        
        if not perm_system.can_user_access_power_level(user.id, required_power, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required power level {required_power} not met"
            )
        return user
    return power_dependency

# COMMON PERMISSION IDs
class CommonPermissionIds:
    FLASHCARD_VIEW = 5001
    FLASHCARD_ANALYTICS = 5002
    FLASHCARD_EXPORT = 5003
    FLASHCARD_CREATE = 5007
    FLASHCARD_EDIT = 5008
    FLASHCARD_DELETE = 5009
    FLASHCARD_IMPORT = 5010
    FLASHCARD_EXPORT_CARDS = 5011
    PORTFOLIO_VIEW = 6001
    PORTFOLIO_CREATE = 6002
    PORTFOLIO_EDIT = 6003
    PORTFOLIO_DELETE = 6004
    PORTFOLIO_PUBLISH = 6005
    USER_VIEW = 8001
    USER_MANAGE = 8002
    USER_ADMIN = 8003
    ADMIN_ACCESS = 9001

# ROLE TEMPLATES
ROLE_TEMPLATES = {
    'content_viewer': {
        'name': 'Content Viewer',
        'description': 'Can view all content but cannot modify',
        'permission_ids': [5001, 5004, 6001, 7001],
        'power_level': 10
    },
    'content_creator': {
        'name': 'Content Creator',
        'description': 'Can create and edit content',
        'permission_ids': [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 6001, 6002, 6003, 7001, 7002],
        'power_level': 30
    },
    'user_manager': {
        'name': 'User Manager', 
        'description': 'Can manage users and their permissions',
        'permission_ids': [8001, 8002, 7001, 7002],
        'power_level': 80
    },
    'system_admin': {
        'name': 'System Administrator',
        'description': 'Full system access and administration',
        'permission_ids': [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011, 6001, 6002, 6003, 6004, 6005, 8001, 8002, 8003, 9001, 7001, 7002],
        'power_level': 100
    }
}
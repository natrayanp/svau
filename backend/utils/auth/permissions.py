from typing import Set, List, Dict, Any, Optional, Tuple
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from .middleware import get_current_user
from utils.database import get_db
from utils.database.query_manager import permission_query
from models.auth_models import User
import json

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

class DatabasePermissionSystem:
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache
    
    def get_permission_structure_from_db(self, db) -> Dict[str, Any]:
        """Get complete permission structure - converts int IDs to string for frontend"""
        cache_key = "permission_structure"
        cached = self._get_cached_structure(db, cache_key)
        
        if cached:
            return cached
        
        structure = self._build_structure_from_db(db)
        self._cache_structure(db, cache_key, structure)
        return structure
    
    def _build_structure_from_db(self, db) -> Dict[str, Any]:
        """Build permission structure - CONVERTS ALL IDs TO STRING FOR FRONTEND"""
        try:
            # ✅ USING QUERY MANAGER
            modules_data = db.execute_query(
                permission_query("GET_PERMISSION_MODULES"),
                fetch=True
            )
            
            modules = []
            total_menus = 0
            total_cards = 0
            total_permissions = 0
            
            for module in modules_data:
                # Convert to string for frontend
                module_id_str = str(module['id'])
                
                # ✅ USING QUERY MANAGER
                menus_data = db.execute_query(
                    permission_query("GET_PERMISSION_MENUS"),
                    (module['id'],),  # DB uses int
                    fetch=True
                )
                
                menus = []
                for menu in menus_data:
                    menu_id_str = str(menu['id'])  # Convert to string
                    
                    # ✅ USING QUERY MANAGER
                    cards_data = db.execute_query(
                        permission_query("GET_PERMISSION_CARDS"),
                        (menu['id'],),  # DB uses int
                        fetch=True
                    )
                    
                    cards = []
                    for card in cards_data:
                        card_id_str = str(card['id'])  # Convert to string
                        
                        # ✅ USING QUERY MANAGER
                        permissions_data = db.execute_query(
                            permission_query("GET_CARD_PERMISSIONS"),
                            (card['id'],),  # DB uses int
                            fetch=True
                        )
                        
                        permissions = []
                        for perm in permissions_data:
                            # Convert permission ID to string for frontend
                            permissions.append({
                                "id": str(perm['id']),  # ← CONVERT TO STRING
                                "action": perm['permission_action'],
                                "display_name": perm['display_name'],
                                "description": perm['description'],
                                "power_level": perm['power_level'],
                                "default_roles": json.loads(perm['default_roles']) if isinstance(perm['default_roles'], str) else perm['default_roles'],
                                "card_id": card_id_str,
                                "card_name": card['name'],
                                "menu_name": menu['name'],
                                "module_name": module['name']
                            })
                        
                        cards.append({
                            "id": card_id_str,  # Already string
                            "key": card['key'],
                            "name": card['name'],
                            "description": card['description'],
                            "display_order": card['display_order'],
                            "menu_id": str(card['menu_id']),  # Convert to string
                            "permissions": permissions
                        })
                        
                        total_permissions += len(permissions)
                        total_cards += 1
                    
                    # ✅ USING QUERY MANAGER
                    menu_permissions_data = db.execute_query(
                        permission_query("GET_MENU_PERMISSIONS"),
                        (menu['id'],),  # DB uses int
                        fetch=True
                    )
                    
                    menu_permissions = []
                    for perm in menu_permissions_data:
                        menu_permissions.append({
                            "id": str(perm['id']),  # ← CONVERT TO STRING
                            "action": perm['permission_action'],
                            "display_name": perm['display_name'],
                            "description": perm['description'],
                            "power_level": perm['power_level'],
                            "default_roles": json.loads(perm['default_roles']) if isinstance(perm['default_roles'], str) else perm['default_roles'],
                            "menu_id": menu_id_str,
                            "menu_name": menu['name'],
                            "module_name": module['name']
                        })
                    
                    menus.append({
                        "id": menu_id_str,  # Already string
                        "key": menu['key'],
                        "name": menu['name'],
                        "description": menu['description'],
                        "display_order": menu['display_order'],
                        "module_id": str(menu['module_id']),  # Convert to string
                        "permissions": menu_permissions,
                        "cards": cards
                    })
                    
                    total_permissions += len(menu_permissions)
                    total_menus += 1
                
                modules.append({
                    "id": module_id_str,  # Already string
                    "key": module['key'],
                    "name": module['name'],
                    "icon": module['icon'],
                    "color": module['color'],
                    "description": module['description'],
                    "display_order": module['display_order'],
                    "menus": menus
                })
            
            return {
                "modules": modules,
                "metadata": {
                    "total_modules": len(modules),
                    "total_menus": total_menus,
                    "total_cards": total_cards,
                    "total_permissions": total_permissions,
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            print(f"Error building permission structure: {e}")
            raise
    
    def _get_cached_structure(self, db, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached permission structure"""
        try:
            # ✅ USING QUERY MANAGER
            cached = db.execute_single(
                permission_query("GET_CACHE"),
                (cache_key,)
            )
            if cached and cached['cache_data']:
                return json.loads(cached['cache_data'])
        except Exception as e:
            print(f"Cache read error: {e}")
        return None
    
    def _cache_structure(self, db, cache_key: str, structure: Dict[str, Any]):
        """Cache permission structure"""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=self.cache_ttl)
            # ✅ USING QUERY MANAGER
            db.execute_insert(
                permission_query("SET_CACHE"),
                (cache_key, json.dumps(structure), expires_at)
            )
        except Exception as e:
            print(f"Failed to cache permission structure: {e}")
    
    # CONVERSION UTILITIES
    def _string_to_int_id(self, permission_id: str) -> int:
        """Convert frontend string ID to backend int ID"""
        try:
            return int(permission_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid permission ID format: {permission_id}")
    
    def _int_to_string_id(self, permission_id: int) -> str:
        """Convert backend int ID to frontend string ID"""
        return str(permission_id)
    
    def _convert_string_ids_to_int(self, permission_ids: List[str]) -> List[int]:
        """Convert list of string IDs to int IDs for database"""
        return [self._string_to_int_id(pid) for pid in permission_ids]
    
    def _convert_int_ids_to_string(self, permission_ids: List[int]) -> List[str]:
        """Convert list of int IDs to string IDs for frontend"""
        return [self._int_to_string_id(pid) for pid in permission_ids]
    
    # DATABASE METHODS WITH CONVERSION
    def get_role_permissions_from_db(self, role_key: str, db) -> Set[str]:  # Returns string IDs
        """Get role permissions - returns string IDs for frontend"""
        try:
            # ✅ USING QUERY MANAGER
            permissions = db.execute_query(
                permission_query("GET_ROLE_PERMISSIONS"),
                (role_key,),
                fetch=True
            )
            # Convert to string IDs for frontend
            return {self._int_to_string_id(row['permission_id']) for row in permissions}
        except Exception as e:
            print(f"Error getting role permissions: {e}")
            return set()
    
    def save_role_permissions_to_db(self, role_key: str, permission_ids: List[str], granted_by: int, db) -> bool:
        """Save role permissions - accepts string IDs, converts to int for DB"""
        try:
            # Convert string IDs to int for database
            permission_ids_int = self._convert_string_ids_to_int(permission_ids)
            
            db.execute_query("BEGIN")
            
            # ✅ USING QUERY MANAGER
            # Clear existing permissions
            db.execute_update(
                permission_query("DELETE_ROLE_PERMISSIONS"),
                (role_key,)
            )
            
            # Insert new permissions
            for perm_id in permission_ids_int:
                # ✅ USING QUERY MANAGER
                db.execute_insert(
                    permission_query("INSERT_ROLE_PERMISSION"),
                    (role_key, perm_id, granted_by)
                )
            
            # ✅ USING QUERY MANAGER
            # Clear cache
            db.execute_update(
                permission_query("DELETE_CACHE"),
                (f'role_permissions_{role_key}%',)
            )
            
            db.execute_query("COMMIT")
            return True
            
        except Exception as e:
            db.execute_query("ROLLBACK")
            print(f"Failed to save role permissions: {e}")
            return False
        
    def get_permission_details(self, permission_id: str, db) -> Optional[Dict[str, Any]]:
        """Get permission details - accepts string ID"""
        try:
            perm_id_int = self._string_to_int_id(permission_id)
            # ✅ USING QUERY MANAGER
            permission = db.execute_single(
                permission_query("GET_PERMISSION_DETAILS"),
                (perm_id_int,)
            )
            
            if permission:
                return {
                    "id": self._int_to_string_id(permission['id']),  # Convert to string
                    "action": permission['permission_action'],
                    "display_name": permission['display_name'],
                    "description": permission['description'],
                    "power_level": permission['power_level'],
                    "module_name": permission['module_name'],
                    "menu_name": permission['menu_name'],
                    "card_name": permission['card_name'],
                    "module_id": self._int_to_string_id(permission['module_id']) if permission['module_id'] else None,
                    "menu_id": self._int_to_string_id(permission['menu_id']) if permission['menu_id'] else None,
                    "card_id": self._int_to_string_id(permission['card_id']) if permission['card_id'] else None
                }
        except Exception as e:
            print(f"Error getting permission details: {e}")
        return None

    def validate_permission_id(self, permission_id: str, db) -> bool:
        """Validate permission ID - accepts string ID"""
        try:
            perm_id_int = self._string_to_int_id(permission_id)
            # ✅ USING QUERY MANAGER
            permission = db.execute_single(
                permission_query("VALIDATE_PERMISSION"),
                (perm_id_int,)
            )
            return permission is not None
        except (ValueError, TypeError):
            return False

    def get_permission_power(self, permission_id: str, db) -> int:
        """Get power level - accepts string ID"""
        perm_details = self.get_permission_details(permission_id, db)
        return perm_details.get("power_level", 0) if perm_details else 0

    def get_max_power_from_permissions(self, permission_ids: List[str], db) -> int:
        """Get maximum power level - accepts string IDs"""
        if not permission_ids:
            return 0
        
        max_power = 0
        for perm_id in permission_ids:
            power = self.get_permission_power(perm_id, db)
            max_power = max(max_power, power)
        
        return max_power

    def get_all_permissions_with_power(self, db, max_power: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all permissions - returns string IDs"""
        try:
            if max_power is not None:
                # ✅ USING QUERY MANAGER
                permissions = db.execute_query(
                    permission_query("GET_PERMISSIONS_BY_POWER"),
                    (max_power,),
                    fetch=True
                )
            else:
                # ✅ USING QUERY MANAGER
                permissions = db.execute_query(
                    permission_query("GET_ALL_PERMISSIONS"),
                    fetch=True
                )
            
            return [
                {
                    "id": self._int_to_string_id(perm['id']),  # Convert to string
                    "action": perm['permission_action'],
                    "display_name": perm['display_name'],
                    "description": perm['description'],
                    "power_level": perm['power_level']
                }
                for perm in permissions
            ]
        except Exception as e:
            print(f"Error getting all permissions: {e}")
            return []

class ExplicitPermissionSystem:
    def __init__(self):
        self.db_system = DatabasePermissionSystem()
    
    # CONVERSION WRAPPERS
    def _ensure_string_id(self, permission_id) -> str:
        """Ensure permission ID is string (convert if int)"""
        if isinstance(permission_id, int):
            return str(permission_id)
        return permission_id
    
    def _ensure_string_ids(self, permission_ids) -> List[str]:
        """Ensure all permission IDs are strings"""
        return [self._ensure_string_id(pid) for pid in permission_ids]
    
    def get_user_permission_ids(self, user_id: int, db) -> Set[str]:  # Returns string IDs
        """Get user's direct permission IDs - returns string IDs"""
        try:
            # ✅ USING QUERY MANAGER
            permissions = db.execute_query(
                permission_query("GET_USER_PERMISSIONS"),
                (user_id,),
                fetch=True
            )
            # Convert to string IDs
            return {self.db_system._int_to_string_id(row['permission_id']) for row in permissions}
        except Exception as e:
            print(f"Error getting user permissions: {e}")
            return set()

    def get_user_permission_ids_with_roles(self, user_id: int, db) -> Set[str]:  # Returns string IDs
        """Get combined permission IDs - returns string IDs"""
        user_permissions = self.get_user_permission_ids(user_id, db)
        
        try:
            # ✅ USING QUERY MANAGER
            user_data = db.execute_single(
                permission_query("GET_USER_ROLE"),
                (user_id,),
                fetch=True
            )
            
            if not user_data:
                return user_permissions
                
            user_role = user_data['role']
            role_permissions = self.db_system.get_role_permissions_from_db(user_role, db)
            
            return user_permissions.union(role_permissions)
        except Exception as e:
            print(f"Error getting user permissions with roles: {e}")
            return user_permissions

    def get_permission_structure(self, db) -> Dict[str, Any]:
        """Get permission structure from database"""
        return self.db_system.get_permission_structure_from_db(db)
    
    def save_role_permissions(self, role_key: str, permission_ids: List[str], granted_by: int, db) -> bool:
        """Save role permissions to database - accepts string IDs"""
        return self.db_system.save_role_permissions_to_db(role_key, permission_ids, granted_by, db)
    
    def get_permission_details(self, permission_id: str, db) -> Optional[Dict[str, Any]]:
        """Get permission details by ID - accepts string ID"""
        return self.db_system.get_permission_details(permission_id, db)
    
    def validate_permission_id(self, permission_id: str, db) -> bool:
        """Validate permission ID exists - accepts string ID"""
        return self.db_system.validate_permission_id(permission_id, db)

    def check_permission_by_id(self, user_permission_ids: Set[str], permission_id: str) -> bool:
        """Direct ID-based permission check - uses string IDs"""
        return permission_id in user_permission_ids

    def get_permission_power(self, permission_id: str, db) -> int:
        """Get power level of a permission with database context - accepts string ID"""
        return self.db_system.get_permission_power(permission_id, db)

    def get_max_power_from_permissions(self, permission_ids: List[str], db) -> int:
        """Get maximum power level from a list of permission IDs - accepts string IDs"""
        return self.db_system.get_max_power_from_permissions(permission_ids, db)

    def get_allowed_child_permissions(self, parent_permission_ids: List[str], db) -> List[Dict[str, Any]]:
        """Get permissions that children can have based on parent's max power - accepts string IDs"""
        max_parent_power = self.get_max_power_from_permissions(parent_permission_ids, db)
        return self.db_system.get_all_permissions_with_power(db, max_parent_power)

    def validate_child_permissions(self, parent_permission_ids: List[str], child_permission_ids: List[str], db) -> Dict[str, Any]:
        """Validate if child permissions are allowed by parent constraints - accepts string IDs"""
        max_parent_power = self.get_max_power_from_permissions(parent_permission_ids, db)
        
        validation_results = []
        all_allowed = True
        
        for child_perm_id in child_permission_ids:
            child_perm = self.db_system.get_permission_details(child_perm_id, db)
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
            else:
                validation_results.append({
                    "permission_id": child_perm_id,
                    "permission_name": "Unknown",
                    "power_level": 0,
                    "is_allowed": False,
                    "reason": "Permission ID not found"
                })
                all_allowed = False
        
        return {
            "max_parent_power": max_parent_power,
            "validation_results": validation_results,
            "all_allowed": all_allowed
        }

    def get_user_max_power(self, user_id: int, db) -> int:
        """Get the maximum power level a user has across all permissions"""
        user_permission_ids = self.get_user_permission_ids_with_roles(user_id, db)
        return self.get_max_power_from_permissions(list(user_permission_ids), db)

    def can_user_access_power_level(self, user_id: int, required_power: int, db) -> bool:
        """Check if user has permissions with sufficient power level"""
        user_max_power = self.get_user_max_power(user_id, db)
        return user_max_power >= required_power

    def get_default_permissions_for_new_module(self, db) -> List[str]:
        """Get default permissions for a new module (least powerful) - returns string IDs"""
        try:
            # ✅ USING QUERY MANAGER
            permissions = db.execute_query(
                permission_query("GET_DEFAULT_PERMISSIONS"),
                fetch=True
            )
            return [self.db_system._int_to_string_id(row['id']) for row in permissions]  # Convert to string
        except Exception as e:
            print(f"Error getting default permissions: {e}")
            return []

    def get_permissions_following_parent(self, parent_permission_ids: List[str], available_permission_ids: List[str], db) -> List[str]:
        """Get permissions that follow parent's permissions within constraints - uses string IDs"""
        if not parent_permission_ids:
            return available_permission_ids
        
        max_parent_power = self.get_max_power_from_permissions(parent_permission_ids, db)
        following_permissions = []
        
        for perm_id in available_permission_ids:
            perm_power = self.get_permission_power(perm_id, db)
            if perm_power <= max_parent_power:
                following_permissions.append(perm_id)
        
        return following_permissions

    def validate_bulk_permissions(self, user_id: int, permission_ids: List[str], db) -> Dict[str, Any]:
        """Bulk validate permissions for a user - accepts string IDs"""
        user_permissions = self.get_user_permission_ids_with_roles(user_id, db)
        results = {}
        
        for perm_id in permission_ids:
            perm_details = self.get_permission_details(perm_id, db)
            results[perm_id] = {
                'has_permission': perm_id in user_permissions,
                'permission_details': perm_details,
                'power_level': perm_details.get('power_level', 0) if perm_details else 0
            }
        
        return {
            'user_id': user_id,
            'total_checked': len(permission_ids),
            'permissions_granted': sum(1 for result in results.values() if result['has_permission']),
            'results': results
        }

    def get_user_permissions_summary(self, user_id: int, db) -> Dict[str, Any]:
        """Get comprehensive user permissions summary - returns string IDs"""
        user_permission_ids = self.get_user_permission_ids_with_roles(user_id, db)
        
        permission_details = []
        total_power = 0
        max_power = 0
        
        for perm_id in user_permission_ids:
            perm_details = self.get_permission_details(perm_id, db)
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
            "user_id": user_id,
            "total_permissions": len(permission_details),
            "max_power": max_power,
            "average_power": round(avg_power, 2),
            "power_distribution": power_distribution,
            "permissions": permission_details
        }

# Keep RolePermissions class for backward compatibility
class RolePermissions:
    @staticmethod
    def get_permission_ids_for_role(role: str, db) -> Set[str]:  # Returns string IDs
        """Role permissions as IDs with power levels - returns string IDs"""
        try:
            # ✅ USING QUERY MANAGER
            permissions = db.execute_query(
                permission_query("GET_ROLE_PERMISSIONS"),
                (role,),
                fetch=True
            )
            # Convert to string IDs
            return {str(row['permission_id']) for row in permissions}
        except Exception as e:
            print(f"Error getting role permissions: {e}")
            return set()

    @staticmethod
    def get_role_power_analysis(role: str, db) -> Dict[str, Any]:
        """Get power analysis for a role - uses string IDs"""
        perm_system = ExplicitPermissionSystem()
        role_permissions = RolePermissions.get_permission_ids_for_role(role, db)
        
        permission_details = []
        total_power = 0
        max_power = 0
        
        for perm_id in role_permissions:
            perm_details = perm_system.db_system.get_permission_details(perm_id, db)
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
    def find_permission_conflicts(role_permissions: Dict[str, Set[str]], db) -> List[Dict[str, Any]]:
        """Find permission conflicts between roles - uses string IDs"""
        conflicts = []
        roles = list(role_permissions.keys())
        perm_system = ExplicitPermissionSystem()
        
        for i, role1 in enumerate(roles):
            for role2 in roles[i+1:]:
                perms1 = role_permissions[role1]
                perms2 = role_permissions[role2]
                
                # Find common permissions
                common_perms = perms1.intersection(perms2)
                
                for perm_id in common_perms:
                    perm_details = perm_system.db_system.get_permission_details(perm_id, db)
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

    @staticmethod
    def get_all_roles_analysis(db) -> Dict[str, Any]:
        """Get power analysis for all roles - uses string IDs"""
        roles = ["basic", "creator", "moderator", "admin"]
        role_analyses = []
        
        for role in roles:
            analysis = RolePermissions.get_role_power_analysis(role, db)
            role_analyses.append(analysis)
        
        return {
            "roles": role_analyses,
            "total_roles": len(role_analyses),
            "analyzed_at": datetime.utcnow().isoformat()
        }

# POWER-BASED DEPENDENCIES
def require_permission_id(permission_id: int):
    """ID-based permission dependency - accepts int ID for backend use"""
    async def permission_dependency(
        user: User = Depends(get_current_user),
        db = Depends(get_db)
    ):
        perm_system = ExplicitPermissionSystem()
        user_permission_ids = perm_system.get_user_permission_ids_with_roles(user.id, db)
        
        # Convert permission_id to string for comparison
        permission_id_str = str(permission_id)
        
        if not perm_system.check_permission_by_id(user_permission_ids, permission_id_str):
            # Get permission details for better error message
            perm_details = perm_system.get_permission_details(permission_id_str, db)
            perm_name = perm_details.get('display_name', f'Permission {permission_id}') if perm_details else f'Permission {permission_id}'
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {perm_name}"
            )
        return user
    return permission_dependency

def require_minimum_power(required_power: int):
    """Dependency to require minimum power level"""
    async def power_dependency(
        user: User = Depends(get_current_user),
        db = Depends(get_db)
    ):
        if required_power < 0 or required_power > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Power level must be between 0 and 100"
            )
        
        perm_system = ExplicitPermissionSystem()
        
        if not perm_system.can_user_access_power_level(user.id, required_power, db):
            user_max_power = perm_system.get_user_max_power(user.id, db)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient power level. Required: {required_power}, Your max: {user_max_power}"
            )
        return user
    return power_dependency

def require_any_permission(permission_ids: List[int]):
    """Dependency to require any of the specified permissions - accepts int IDs"""
    async def any_permission_dependency(
        user: User = Depends(get_current_user),
        db = Depends(get_db)
    ):
        perm_system = ExplicitPermissionSystem()
        user_permission_ids = perm_system.get_user_permission_ids_with_roles(user.id, db)
        
        for perm_id in permission_ids:
            # Convert to string for comparison
            perm_id_str = str(perm_id)
            if perm_system.check_permission_by_id(user_permission_ids, perm_id_str):
                return user
        
        # If none of the permissions are granted
        permission_names = []
        for perm_id in permission_ids:
            perm_id_str = str(perm_id)
            perm_details = perm_system.get_permission_details(perm_id_str, db)
            name = perm_details.get('display_name', f'Permission {perm_id}') if perm_details else f'Permission {perm_id}'
            permission_names.append(name)
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires any of these permissions: {', '.join(permission_names)}"
        )
    return any_permission_dependency

def require_all_permissions(permission_ids: List[int]):
    """Dependency to require all of the specified permissions - accepts int IDs"""
    async def all_permissions_dependency(
        user: User = Depends(get_current_user),
        db = Depends(get_db)
    ):
        perm_system = ExplicitPermissionSystem()
        user_permission_ids = perm_system.get_user_permission_ids_with_roles(user.id, db)
        
        missing_permissions = []
        for perm_id in permission_ids:
            # Convert to string for comparison
            perm_id_str = str(perm_id)
            if not perm_system.check_permission_by_id(user_permission_ids, perm_id_str):
                perm_details = perm_system.get_permission_details(perm_id_str, db)
                name = perm_details.get('display_name', f'Permission {perm_id}') if perm_details else f'Permission {perm_id}'
                missing_permissions.append(name)
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        return user
    return all_permissions_dependency

# COMMON PERMISSION IDs (as integers for backend use)
class CommonPermissionIds:
    # Flashcard permissions
    FLASHCARD_VIEW = 5001
    FLASHCARD_ANALYTICS = 5002
    FLASHCARD_EXPORT = 5003
    FLASHCARD_CREATE = 5007
    FLASHCARD_EDIT = 5008
    FLASHCARD_DELETE = 5009
    FLASHCARD_IMPORT = 5010
    FLASHCARD_EXPORT_CARDS = 5011
    
    # Portfolio permissions
    PORTFOLIO_VIEW = 6001
    PORTFOLIO_CREATE = 6002
    PORTFOLIO_EDIT = 6003
    PORTFOLIO_DELETE = 6004
    PORTFOLIO_PUBLISH = 6005
    
    # User management permissions
    USER_VIEW = 8001
    USER_MANAGE = 8002
    USER_ADMIN = 8003
    
    # System administration permissions
    ADMIN_ACCESS = 9001
    SYSTEM_CONFIG = 9002
    AUDIT_VIEW = 9003

# ROLE TEMPLATES (for reference, now stored in database)
ROLE_TEMPLATES = {
    'content_viewer': {
        'name': 'Content Viewer',
        'description': 'Can view all content but cannot modify',
        'permission_ids': [5001, 6001],
        'power_level': 10
    },
    'content_creator': {
        'name': 'Content Creator',
        'description': 'Can create and edit content',
        'permission_ids': [5001, 5002, 5003, 5007, 5008, 6001, 6002, 6003],
        'power_level': 30
    },
    'user_manager': {
        'name': 'User Manager', 
        'description': 'Can manage users and their permissions',
        'permission_ids': [8001, 8002],
        'power_level': 80
    },
    'system_admin': {
        'name': 'System Administrator',
        'description': 'Full system access and administration',
        'permission_ids': [5001, 5002, 5003, 5007, 5008, 5009, 5010, 5011, 6001, 6002, 6003, 6004, 6005, 8001, 8002, 8003, 9001, 9002, 9003],
        'power_level': 100
    }
}

# Utility functions
def get_permission_system() -> ExplicitPermissionSystem:
    """Get a new instance of the permission system"""
    return ExplicitPermissionSystem()

def clear_permission_caches():
    """Clear all permission-related caches"""
    # This would clear any LRU caches if they were used
    # Currently we rely on database-level caching
    pass
"""
Optimized authentication queries - ID-based permissions with power support
"""

# User management queries (unchanged)
CREATE_USER = """
INSERT INTO users (uid, email, display_name, role, email_verified, created_at)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id
"""

GET_USER_BY_UID = "SELECT * FROM users WHERE uid = %s"
GET_USER_BY_EMAIL = "SELECT * FROM users WHERE email = %s"
GET_USER_BY_ID = "SELECT * FROM users WHERE id = %s"
UPDATE_USER = "UPDATE users SET display_name = %s, role = %s, email_verified = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
DELETE_USER = "DELETE FROM users WHERE id = %s"
GET_ALL_USERS = "SELECT * FROM users ORDER BY created_at DESC"

# OPTIMIZED PERMISSION QUERIES - ID-BASED WITH POWER SUPPORT
GET_USER_PERMISSION_IDS = """
SELECT permission_id 
FROM user_permissions 
WHERE user_id = %s 
ORDER BY permission_id
"""

ADD_USER_PERMISSION = """
INSERT INTO user_permissions (user_id, permission_id, granted_by)
VALUES (%s, %s, %s)
ON CONFLICT (user_id, permission_id) DO UPDATE 
SET granted_by = EXCLUDED.granted_by,
    granted_at = CURRENT_TIMESTAMP
RETURNING id
"""

REMOVE_USER_PERMISSION = """
DELETE FROM user_permissions 
WHERE user_id = %s AND permission_id = %s
RETURNING id
"""

REMOVE_USER_PERMISSIONS_BULK = """
DELETE FROM user_permissions 
WHERE user_id = %s AND permission_id = ANY(%s)
RETURNING id
"""

CHECK_PERMISSION = """
SELECT 1 FROM user_permissions 
WHERE user_id = %s AND permission_id = %s
"""

LOG_PERMISSION_ACTION = """
INSERT INTO permission_audit (user_id, permission_id, action, performed_by)
VALUES (%s, %s, %s, %s)
"""

GET_PERMISSION_AUDIT = """
SELECT 
    pa.*,
    u.display_name as performed_by_name
FROM permission_audit pa
JOIN users u ON pa.performed_by = u.id
WHERE pa.user_id = %s
ORDER BY pa.performed_at DESC
"""


# NEW QUERIES FOR POWER-BASED SYSTEM
GET_USERS_BY_ROLE = """
SELECT id, email, display_name, role, created_at 
FROM users 
WHERE role = %s 
ORDER BY created_at DESC
"""

GET_ROLE_STATISTICS = """
SELECT role, COUNT(*) as user_count 
FROM users 
GROUP BY role 
ORDER BY user_count DESC
"""

# PERMISSION STRUCTURE QUERIES
GET_PERMISSION_MODULES = "SELECT * FROM permission_modules WHERE is_active = TRUE ORDER BY display_order"

GET_PERMISSION_MENUS = "SELECT * FROM permission_menus WHERE module_id = %s AND is_active = TRUE ORDER BY display_order"

GET_PERMISSION_CARDS = "SELECT * FROM permission_cards WHERE menu_id = %s AND is_active = TRUE ORDER BY display_order"

GET_CARD_PERMISSIONS = """
SELECT p.* FROM permissions p 
WHERE p.card_id = %s AND p.is_active = TRUE 
ORDER BY p.display_order
"""

GET_MENU_PERMISSIONS = """
SELECT p.* FROM permissions p 
WHERE p.menu_id = %s AND p.card_id IS NULL AND p.is_active = TRUE 
ORDER BY p.display_order
"""

# ROLE PERMISSION QUERIES
GET_ROLE_PERMISSIONS = "SELECT permission_id FROM role_permissions WHERE role_key = %s"

DELETE_ROLE_PERMISSIONS = "DELETE FROM role_permissions WHERE role_key = %s"

INSERT_ROLE_PERMISSION = "INSERT INTO role_permissions (role_key, permission_id, granted_by) VALUES (%s, %s, %s)"

# PERMISSION DETAIL QUERIES
GET_PERMISSION_DETAILS = """
SELECT p.*, pm.name as module_name, pmenu.name as menu_name, pc.name as card_name
FROM permissions p
LEFT JOIN permission_modules pm ON p.module_id = pm.id
LEFT JOIN permission_menus pmenu ON p.menu_id = pmenu.id
LEFT JOIN permission_cards pc ON p.card_id = pc.id
WHERE p.id = %s
"""

VALIDATE_PERMISSION = "SELECT id FROM permissions WHERE id = %s AND is_active = TRUE"

GET_ALL_PERMISSIONS = "SELECT * FROM permissions WHERE is_active = TRUE ORDER BY power_level, display_name"

GET_PERMISSIONS_BY_POWER = "SELECT * FROM permissions WHERE is_active = TRUE AND power_level <= %s ORDER BY power_level, display_name"

# CACHE QUERIES
GET_CACHE = "SELECT cache_data FROM permission_cache WHERE cache_key = %s AND expires_at > CURRENT_TIMESTAMP"

SET_CACHE = """
INSERT INTO permission_cache (cache_key, cache_data, expires_at) 
VALUES (%s, %s, %s)
ON CONFLICT (cache_key) DO UPDATE 
SET cache_data = EXCLUDED.cache_data, 
    expires_at = EXCLUDED.expires_at,
    created_at = CURRENT_TIMESTAMP
"""

DELETE_CACHE = "DELETE FROM permission_cache WHERE cache_key LIKE %s"

# USER PERMISSION QUERIES (ENHANCED)
GET_USER_PERMISSIONS = "SELECT permission_id FROM user_permissions WHERE user_id = %s"

GET_USER_ROLE = "SELECT role FROM users WHERE id = %s"

# DEFAULT PERMISSIONS QUERY
GET_DEFAULT_PERMISSIONS = "SELECT id FROM permissions WHERE power_level <= 20 AND is_active = TRUE ORDER BY power_level LIMIT 5"
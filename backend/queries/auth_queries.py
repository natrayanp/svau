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

GET_USER_PERMISSIONS_WITH_DETAILS = """
SELECT 
    up.permission_id,
    cp.display_name,
    cp.description,
    cp.permission_action,
    cp.power_level
FROM user_permissions up
LEFT JOIN card_permissions cp ON up.permission_id = cp.id
WHERE up.user_id = %s
ORDER BY cp.power_level DESC, cp.display_name
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
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
GET_PERMISSION_MODULES = """
WITH recursive_structure AS (
    SELECT 
        ps.permissstruct_id, ps.record_type, ps.key, ps.name, ps.description,
        ps.icon, ps.color, ps.allowed_actions, 
        ps.parent_id, ps.display_order,
        NULL as parent_name,
        1 as level
    FROM permission_structures ps
    WHERE ps.record_type = 'module' AND ps.is_active = true
    
    UNION ALL
    
    SELECT 
        child.permissstruct_id, child.record_type, child.key, child.name, child.description,
        child.icon, child.color, child.allowed_actions,
        child.parent_id, child.display_order,
        parent.name as parent_name,
        parent.level + 1 as level
    FROM permission_structures child
    INNER JOIN recursive_structure parent ON child.parent_id = parent.permissstruct_id
    WHERE child.is_active = true
)
SELECT 
    rs.*,
    action_val as action_key,
    ad.display_name as action_display_name,
    ad.power_level,
    ad.category
FROM recursive_structure rs
CROSS JOIN LATERAL jsonb_array_elements_text(rs.allowed_actions) as action_val
INNER JOIN action_definitions ad ON ad.action_key = action_val
WHERE ad.is_active = true
ORDER BY rs.level, rs.display_order, rs.name, ad.power_level
"""

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
# This is to be changed to get only the roles that are allowed to be viewed by the User (created by the user company)
GET_ROLE_PERMISSIONS = """
SELECT 
    rp.role_id,
    COUNT(DISTINCT rp.structure_id) as permission_count,
    -- Check if this role has any template permissions
    BOOL_OR(rp.is_template) as has_templates,
    COUNT(DISTINCT ur.user_id) as user_count,
    -- Get template info if any
    MAX(rp.template_name) as template_name,
    MAX(rp.template_description) as template_description
FROM role_permissions rp
LEFT JOIN user_roles ur ON rp.role_id = ur.role_id
WHERE rp.is_template = false  -- Only show non-template role assignments
GROUP BY rp.role_id
ORDER BY permission_count DESC
"""



DELETE_ROLE_PERMISSIONS = "DELETE FROM role_permissions WHERE role_id = %s"

INSERT_ROLE_PERMISSION = "INSERT INTO role_permissions (role_id, permission_id, granted_by) VALUES (%s, %s, %s)"

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

GET_USER_ROLE = "SELECT role_id FROM user_roles WHERE user_id = %s"

# DEFAULT PERMISSIONS QUERY
GET_DEFAULT_PERMISSIONS = "SELECT id FROM permissions WHERE power_level <= 20 AND is_active = TRUE ORDER BY power_level LIMIT 5"

#/structure



PERMISSION_STRUCTURE_QUERY = """
WITH module_data AS (
    SELECT 
        permissstruct_id as id,
        record_type,
        key,
        name,
        description,
        icon,
        color,
        display_order,
        allowed_actions
    FROM permission_structures 
    WHERE record_type = 'module' AND is_active = true
    ORDER BY display_order
),
menu_data AS (
    SELECT 
        ps.permissstruct_id as id,
        ps.record_type,
        ps.key,
        ps.name,
        ps.description,
        ps.display_order,
        ps.parent_id as module_id,
        ps.allowed_actions
    FROM permission_structures ps
    WHERE ps.record_type = 'menu' AND ps.is_active = true
    ORDER BY ps.display_order
),
card_data AS (
    SELECT 
        ps.permissstruct_id as id,
        ps.record_type,
        ps.key,
        ps.name,
        ps.description,
        ps.display_order,
        ps.parent_id as menu_id,
        ps.allowed_actions
    FROM permission_structures ps
    WHERE ps.record_type = 'card' AND ps.is_active = true
    ORDER BY ps.display_order
),
action_details AS (
    SELECT 
        ps.permissstruct_id,
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'action_key', ad.action_key,
                'display_name', ad.display_name,
                'power_level', ad.power_level,
                'category', ad.category
            )
        ) as action_details
    FROM permission_structures ps
    CROSS JOIN LATERAL jsonb_array_elements_text(ps.allowed_actions) as action_val
    INNER JOIN action_definitions ad ON ad.action_key = action_val
    WHERE ad.is_active = true
    GROUP BY ps.permissstruct_id
)
SELECT 
    JSON_BUILD_OBJECT(
        'modules', (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'id', md.id::text,
                    'record_type', md.record_type,
                    'key', md.key,
                    'name', md.name,
                    'description', md.description,
                    'icon', md.icon,
                    'color', md.color,
                    'display_order', md.display_order,
                    'allowed_actions', COALESCE(ad.action_details, '[]'::json),
                    'menus', COALESCE((
                        SELECT JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'id', m.id::text,
                                'record_type', m.record_type,
                                'key', m.key,
                                'name', m.name,
                                'description', m.description,
                                'display_order', m.display_order,
                                'module_id', m.module_id::text,
                                'allowed_actions', COALESCE(ad2.action_details, '[]'::json),
                                'cards', COALESCE((
                                    SELECT JSON_AGG(
                                        JSON_BUILD_OBJECT(
                                            'id', c.id::text,
                                            'record_type', c.record_type,
                                            'key', c.key,
                                            'name', c.name,
                                            'description', c.description,
                                            'display_order', c.display_order,
                                            'menu_id', c.menu_id::text,
                                            'allowed_actions', COALESCE(ad3.action_details, '[]'::json)
                                        )
                                        ORDER BY c.display_order
                                    )
                                    FROM card_data c
                                    LEFT JOIN action_details ad3 ON c.id = ad3.permissstruct_id
                                    WHERE c.menu_id = m.id
                                ), '[]'::json)
                            )
                            ORDER BY m.display_order
                        )
                        FROM menu_data m
                        LEFT JOIN action_details ad2 ON m.id = ad2.permissstruct_id
                        WHERE m.module_id = md.id
                    ), '[]'::json)
                )
                ORDER BY md.display_order
            )
            FROM module_data md
            LEFT JOIN action_details ad ON md.id = ad.permissstruct_id
        ),
        'metadata', JSON_BUILD_OBJECT(
            'total_modules', (SELECT COUNT(*) FROM module_data),
            'total_menus',   (SELECT COUNT(*) FROM menu_data),
            'total_cards',   (SELECT COUNT(*) FROM card_data),
            'total_permissions', (
                SELECT COUNT(*) 
                FROM permission_structures ps
                WHERE ps.is_active = true
            ),
            'last_updated', NOW()::text
        )
    ) as permission_structure;
"""

#---------------------------------------#
#  ROLES RELATED QUERIES - START        #
#---------------------------------------#
ORGANIZATION_ROLES_QUERY = """
WITH user_organization AS (
    SELECT org_id
    FROM users
    WHERE user_id = %(current_user_id)s
),
active_package_menus AS (
    SELECT 
        p.org_id,
        p.allowed_menu_ids
    FROM packages p
    WHERE p.org_id = (SELECT org_id FROM user_organization)
      AND p.status = 'AC'
      AND CURRENT_DATE BETWEEN p.effective_date 
          AND (p.expiry_date + INTERVAL '1 day' * p.grace_period_days)
    ORDER BY p.created_at DESC
    LIMIT 1
),
filtered_permission_structures AS (
    SELECT DISTINCT ps.permissstruct_id AS id
    FROM permission_structures ps
    CROSS JOIN active_package_menus apm
    WHERE ps.record_type = 'module'
       OR ps.permissstruct_id = ANY(
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       )
       OR (ps.record_type = 'card' AND ps.parent_id IN (
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       ))
),
role_permission_counts AS (
    SELECT 
        r.role_id,
        COUNT(DISTINCT rp.structure_id) AS permission_count,
        COALESCE(
            JSON_AGG(
                JSON_BUILD_OBJECT(
                    'permissstruct_id', rp.structure_id::text,
                    'granted_action_key', rp.granted_actions
                )
            ) FILTER (WHERE rp.structure_id IS NOT NULL),  -- <-- ignore nulls
            '[]'::json
        ) AS permission_ids
    FROM roles r
    LEFT JOIN role_permissions rp 
           ON rp.role_id = r.role_id
    LEFT JOIN permission_structures ps 
           ON rp.structure_id = ps.permissstruct_id
          AND ps.permissstruct_id IN (SELECT id FROM filtered_permission_structures)
    WHERE r.is_active = TRUE
      AND r.org_id = (SELECT org_id FROM user_organization)
    GROUP BY r.role_id
),
role_user_counts AS (
    SELECT
        r.role_id,
        COUNT(ur.user_id) AS user_count
    FROM roles r
    LEFT JOIN user_roles ur 
           ON ur.role_id = r.role_id
    LEFT JOIN users u 
           ON ur.user_id = u.user_id AND u.status = 'AC'
    WHERE r.is_active = TRUE
      AND r.org_id = (SELECT org_id FROM user_organization)
    GROUP BY r.role_id
),
role_details AS (
    SELECT 
        r.role_id,
        r.org_id,
        r.display_name,
        r.description,
        r.is_system_role,
        r.is_template,
        r.template_id,
        r.template_name,
        r.created_at,
        o.name AS organization_name,
        COALESCE(rpc.permission_count, 0) AS permission_count,
        COALESCE(rpc.permission_ids, '[]'::json) AS permission_ids,
        COALESCE(ruc.user_count, 0) AS user_count
    FROM roles r
    JOIN organizations o ON r.org_id = o.org_id
    LEFT JOIN role_permission_counts rpc 
        ON r.role_id = rpc.role_id
    LEFT JOIN role_user_counts ruc 
        ON r.role_id = ruc.role_id
    WHERE r.is_active = TRUE
      AND r.org_id = (SELECT org_id FROM user_organization)
),
total_count AS (
    SELECT COUNT(*) AS total FROM role_details
),
paged_roles AS (
    SELECT *
    FROM role_details
    ORDER BY display_name
    OFFSET %(offset)s LIMIT %(limit)s
)
SELECT json_build_object(
    'items', (
        SELECT json_agg(
            json_build_object(
                'role_id', pr.role_id::text,
                'organization_id', pr.org_id,
                'display_name', pr.display_name,
                'description', pr.description,
                'is_system_role', pr.is_system_role,
                'is_template', pr.is_template,
                'template_id', pr.template_id,
                'template_name', pr.template_name,
                'organization_name', pr.organization_name,
                'permission_count', pr.permission_count,
                'permission_ids', pr.permission_ids,
                'user_count', pr.user_count,
                'created_at', pr.created_at
            )
        )
        FROM paged_roles pr
    ),
    'total', (SELECT total FROM total_count),
    'offset', %(offset)s,
    'limit', %(limit)s,
    'org_id', (SELECT org_id FROM user_organization),
    'version', json_build_array(
        json_build_object(
            'table_name', 'roles',
            'table_version', (SELECT MAX(table_version) FROM tableversion WHERE table_name = 'roles')
        )
    )
) AS roles_data
"""

ORGANIZATION_ROLES_QUERY_old = """
WITH user_organization AS (
    SELECT org_id 
    FROM users 
    WHERE user_id = %(current_user_id)s
),
active_package_menus AS (
    SELECT 
        p.org_id,
        p.allowed_menu_ids
    FROM packages p
    WHERE p.org_id = (SELECT org_id FROM user_organization)
      AND p.status = 'AC'
      AND CURRENT_DATE BETWEEN p.effective_date 
          AND (p.expiry_date + INTERVAL '1 day' * p.grace_period_days)
    ORDER BY p.created_at DESC
    LIMIT 1
),
filtered_permission_structures AS (
    SELECT DISTINCT ps.permissstruct_id AS id
    FROM permission_structures ps
    CROSS JOIN active_package_menus apm
    WHERE ps.record_type = 'module'
       OR ps.permissstruct_id = ANY(
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       )
       OR (ps.record_type = 'card' AND ps.parent_id IN (
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       ))
),
role_permission_counts AS (
    SELECT 
        r.role_id,
        r.org_id,
        COUNT(DISTINCT rp.structure_id) AS permission_count,
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'permissstruct_id', rp.structure_id::text,
                'granted_action_key', rp.granted_actions
            )
        ) AS permission_ids
    FROM roles r
    JOIN role_permissions rp ON rp.role_id = r.role_id
    JOIN permission_structures ps ON rp.structure_id = ps.permissstruct_id
    WHERE r.is_active = TRUE 
      AND rp.status = 'AC'
      AND ps.permissstruct_id IN (SELECT id FROM filtered_permission_structures)
      AND r.org_id = (SELECT org_id FROM user_organization)
    GROUP BY r.role_id, r.org_id
),
/***********************************************
 Flattened user_roles: one row per role_id
***********************************************/
role_user_counts AS (
    SELECT
        ur.role_id,
        ur.org_id,
        COUNT(DISTINCT ur.user_id) AS user_count
    FROM user_roles ur
    JOIN users u ON ur.user_id = u.user_id
    WHERE u.status = 'AC'
      AND ur.org_id = (SELECT org_id FROM user_organization)
    GROUP BY ur.role_id, ur.org_id
),
role_details AS (
    SELECT 
        r.role_id,
        r.org_id,
        r.display_name,
        r.description,
        r.is_system_role,
        r.is_template,
        r.template_id,
        r.template_name,
        r.created_at,
        o.name AS organization_name,
        COALESCE(rpc.permission_count, 0) AS permission_count,
        COALESCE(rpc.permission_ids, '[]'::json) AS permission_ids,
        COALESCE(ruc.user_count, 0) AS user_count
    FROM roles r
    JOIN organizations o ON r.org_id = o.org_id
    LEFT JOIN role_permission_counts rpc 
        ON r.role_id = rpc.role_id AND r.org_id = rpc.org_id
    LEFT JOIN role_user_counts ruc 
        ON r.role_id = ruc.role_id AND r.org_id = ruc.org_id
    WHERE r.is_active = TRUE
      AND r.org_id = (SELECT org_id FROM user_organization)
),
total_count AS (
    SELECT COUNT(*) AS total FROM role_details
),
paged_roles AS (
    SELECT *
    FROM role_details
    ORDER BY display_name
    OFFSET %(offset)s LIMIT %(limit)s
)
SELECT json_build_object(
    'items', (
        SELECT json_agg(
            json_build_object(
                'role_id', pr.role_id::text,
                'organization_id', pr.org_id,
                'display_name', pr.display_name,
                'description', pr.description,
                'is_system_role', pr.is_system_role,
                'is_template', pr.is_template,
                'template_id', pr.template_id,
                'template_name', pr.template_name,
                'organization_name', pr.organization_name,
                'permission_count', pr.permission_count,
                'permission_ids', pr.permission_ids,
                'user_count', pr.user_count,
                'created_at', pr.created_at
            )
        )
        FROM paged_roles pr
    ),
    'total', (SELECT total FROM total_count),
    'offset', %(offset)s,
    'limit', %(limit)s,
    'org_id', (SELECT org_id FROM user_organization),
    'version', json_build_array(
        json_build_object(
            'table_name', 'roles',
            'table_version', (SELECT MAX(table_version) FROM tableversion WHERE table_name = 'roles')
        )
    )
) AS roles_data
"""

GET_USER_ORGANIZATION = """
SELECT u.org_id, o.name AS org_name, o.status AS org_status
FROM users u
JOIN organizations o ON u.org_id = o.org_id
WHERE u.user_id = %(user_id)s
"""

VERIFY_ROLE_ORGANIZATION = """
SELECT role_id
FROM roles
WHERE role_id = %(role_id)s
  AND org_id = %(org_id)s
  AND is_active = TRUE
"""

CHECK_ROLE_NAME_EXISTS = """
SELECT role_id
FROM roles
WHERE org_id = %(org_id)s
  AND display_name = %(display_name)s
  AND is_active = TRUE
"""

CREATE_NEW_ROLE = """
INSERT INTO roles (org_id, display_name, description, is_system_role, is_template, created_by)
VALUES (%(org_id)s, %(display_name)s, %(description)s, FALSE, FALSE, %(created_by)s)
RETURNING role_id
"""

UPDATE_ROLE_METADATA = """
UPDATE roles
SET {update_fields},
    updated_at = CURRENT_TIMESTAMP,
    updated_by = %(updated_by)s
WHERE role_id = %(role_id)s
"""

UPSERT_ROLE_PERMISSION = """
INSERT INTO role_permissions (role_id, structure_id, granted_actions, status, created_at, updated_at)
VALUES (%(role_id)s, %(structure_id)s, %(granted_actions)s::jsonb, 'AC', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (role_id, structure_id) 
DO UPDATE SET 
    granted_actions = EXCLUDED.granted_actions,
    updated_at = CURRENT_TIMESTAMP,
    status = 'AC'
"""

REMOVE_OLD_PERMISSIONS = """
DELETE FROM role_permissions
WHERE role_id = %(role_id)s
  AND structure_id NOT IN %(structure_ids)s
"""

# Soft delete a role (mark as inactive)
SOFT_DELETE_ROLE = """
UPDATE roles 
SET 
    is_active = FALSE, 
    status = 'DE',
    updated_at = CURRENT_TIMESTAMP,
    updated_by = %(updated_by)s
WHERE role_id = %(role_id)s
  AND org_id = %(org_id)s
  AND is_active = TRUE
  AND is_system_role = FALSE  -- Don't allow deleting system roles
RETURNING role_id
"""

#---------------------------------------#
#  ROLES RELATED QUERIES - END          #
#---------------------------------------#


#---------------------------------------#
#  USERS RELATED QUERIES - START        #
#---------------------------------------#
"""
ORGANIZATION_USERS_QUERY =
WITH current_org AS (
    SELECT org_id
    FROM users
    WHERE user_id = %(current_user_id)s
),
user_base AS (
    SELECT 
        u.user_id,
        u.uid,
        u.email,
        u.display_name,
        u.org_id,
        u.email_verified,
        u.created_at,
        u.updated_at
    FROM users u
    WHERE u.org_id = (SELECT org_id FROM current_org)
      AND u.status = 'AC'
),
user_roles AS (
    SELECT 
        ur.user_id,
        COALESCE(
            json_agg(ur.role_id::text ORDER BY ur.role_id),
            '[]'::json
        ) AS roles
    FROM user_roles ur
    WHERE ur.org_id = (SELECT org_id FROM current_org)
    GROUP BY ur.user_id
),
total_count AS (
    SELECT COUNT(*) AS total
    FROM user_base
),
paged_users AS (
    SELECT *
    FROM user_base u
    ORDER BY u.created_at DESC
    OFFSET %(offset)s LIMIT %(limit)s
)
SELECT json_build_object(
    'items', (
        SELECT json_agg(
            json_build_object(
                'user_id', pu.user_id,
                'uid', pu.uid,
                'email', pu.email,
                'display_name', pu.display_name,
                'org_id', pu.org_id,
                'email_verified', pu.email_verified,
                'created_at', pu.created_at,
                'updated_at', pu.updated_at,
                'roles', COALESCE(ur.roles, '[]'::json)
            )
        )
        FROM paged_users pu
        LEFT JOIN user_roles ur ON pu.user_id = ur.user_id
    ),
    'total', (SELECT total FROM total_count),
    'offset', %(offset)s,
    'limit', %(limit)s,
    'org_id', (SELECT org_id FROM current_org),
    'version', json_build_array(
        json_build_object(
            'table_name', 'users',
            'table_version', (
                SELECT MAX(table_version)
                FROM tableversion
                WHERE table_name = 'users'
                  AND org_id = (SELECT org_id FROM current_org)
            )
        )
    )
) AS users_data
"""

#---------------------------------------#
#  USERS RELATED QUERIES - END          #
#---------------------------------------#
















GET_ROLE_TEMPLATES = """
WITH user_organization AS (
    SELECT organization_id 
    FROM users 
    WHERE id = %s  -- 👈 CURRENT USER ID PARAMETER
),
active_package_menus AS (
    SELECT 
        p.organization_id,
        p.allowed_menu_ids
    FROM packages p
    WHERE p.organization_id = (SELECT organization_id FROM user_organization)
      AND p.status = 'active'
      AND CURRENT_DATE BETWEEN p.effective_date 
          AND (p.expiry_date + INTERVAL '1 day' * p.grace_period_days)
    ORDER BY p.created_at DESC
    LIMIT 1
),
filtered_permission_structures AS (
    SELECT DISTINCT ps.id
    FROM permission_structures ps
    CROSS JOIN active_package_menus apm
    WHERE ps.record_type = 'module'  -- Always allow modules
       OR ps.id = ANY(SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer)  -- Only allowed menus
       OR (ps.record_type = 'card' AND ps.parent_id IN (
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       ))  -- Cards of allowed menus
),
role_template_details AS (
    SELECT 
        rt.template_key,
        rt.name as template_name,
        rt.description,
        rt.permission_ids,
        rt.power_level,
        rt.is_system_template,
        rt.created_at,
        rt.updated_at,
        (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'id', p.id,
                    'action', p.permission_action,
                    'display_name', p.display_name,
                    'power_level', p.power_level,
                    'description', p.description
                )
            )
            FROM permissions p
            WHERE p.id = ANY(rt.permission_ids)
              AND p.id IN (  -- 👈 APPLY PACKAGE FILTERING TO PERMISSIONS
                  SELECT rp.permission_id 
                  FROM role_permissions rp 
                  JOIN permission_structures ps ON rp.structure_id = ps.id
                  WHERE ps.id IN (SELECT id FROM filtered_permission_structures)
              )
        ) as permission_details,
        COUNT(DISTINCT r.id) as roles_using_count
    FROM role_templates rt
    LEFT JOIN roles r ON r.template_id = rt.template_key AND r.is_active = true
    WHERE rt.is_active = true
      AND (
          rt.is_system_template = true  -- 👈 SYSTEM TEMPLATES
          OR EXISTS (  -- 👈 ORGANIZATION-SPECIFIC TEMPLATES
              SELECT 1 FROM roles r2 
              WHERE r2.template_id = rt.template_key 
                AND r2.organization_id = (SELECT organization_id FROM user_organization)
          )
      )
    GROUP BY 
        rt.template_key, 
        rt.name, 
        rt.description, 
        rt.permission_ids, 
        rt.power_level, 
        rt.is_system_template,
        rt.created_at,
        rt.updated_at
)
SELECT 
    JSON_BUILD_OBJECT(
        'templates', (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'template_key', rtd.template_key,
                    'template_name', rtd.template_name,
                    'description', rtd.description,
                    'permission_ids', rtd.permission_ids,
                    'power_level', rtd.power_level,
                    'is_system_template', rtd.is_system_template,
                    'permission_details', rtd.permission_details,
                    'roles_using_count', rtd.roles_using_count,
                    'created_at', rtd.created_at,
                    'updated_at', rtd.updated_at
                )
                ORDER BY rtd.power_level DESC, rtd.template_name
            )
            FROM role_template_details rtd
        ),
        'summary', JSON_BUILD_OBJECT(
            'total_templates', COUNT(*),
            'system_templates', COUNT(*) FILTER (WHERE is_system_template = true),
            'organization_templates', COUNT(*) FILTER (WHERE is_system_template = false),
            'current_organization', (SELECT organization_id FROM user_organization),
            'package_restrictions_applied', true
        )
    ) as templates_data
FROM role_template_details
"""

# For ALL templates
GET_ALL_ROLE_TEMPLATES = """
WITH 
user_organization AS (
    SELECT organization_id FROM users WHERE id = %s
),
active_package_menus AS (
    SELECT organization_id, allowed_menu_ids
    FROM packages 
    WHERE organization_id = (SELECT organization_id FROM user_organization)
      AND status = 'active'
      AND CURRENT_DATE BETWEEN effective_date 
          AND (expiry_date + INTERVAL '1 day' * grace_period_days)
    ORDER BY created_at DESC
    LIMIT 1
),
filtered_permission_structures AS (
    SELECT DISTINCT ps.id
    FROM permission_structures ps
    CROSS JOIN active_package_menus apm
    WHERE ps.record_type = 'module'
       OR ps.id = ANY(SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer)
       OR (ps.record_type = 'card' AND ps.parent_id IN (
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       ))
),
role_template_details AS (
    SELECT 
        rt.template_key,
        rt.name as template_name,
        rt.description,
        rt.permission_ids,
        rt.power_level,
        rt.is_system_template,
        rt.created_at,
        rt.updated_at,
        (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'id', p.id,
                    'action', p.permission_action,
                    'display_name', p.display_name,
                    'power_level', p.power_level,
                    'description', p.description
                )
            )
            FROM permissions p
            WHERE p.id = ANY(rt.permission_ids)
              AND p.id IN (
                  SELECT rp.permission_id 
                  FROM role_permissions rp 
                  WHERE rp.structure_id IN (SELECT id FROM filtered_permission_structures)
              )
        ) as permission_details,
        COUNT(DISTINCT r.id) as roles_using_count
    FROM role_templates rt
    LEFT JOIN roles r ON r.template_id = rt.template_key AND r.is_active = true
    WHERE rt.is_active = true
      AND (
          rt.is_system_template = true
          OR EXISTS (
              SELECT 1 FROM roles r2 
              WHERE r2.template_id = rt.template_key 
                AND r2.organization_id = (SELECT organization_id FROM user_organization)
          )
      )
    GROUP BY rt.template_key, rt.name, rt.description, rt.permission_ids, 
             rt.power_level, rt.is_system_template, rt.created_at, rt.updated_at
)
SELECT 
    JSON_BUILD_OBJECT(
        'templates', (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'template_key', rtd.template_key,
                    'template_name', rtd.template_name,
                    'description', rtd.description,
                    'permission_ids', rtd.permission_ids,
                    'power_level', rtd.power_level,
                    'is_system_template', rtd.is_system_template,
                    'permission_details', rtd.permission_details,
                    'roles_using_count', rtd.roles_using_count,
                    'created_at', rtd.created_at,
                    'updated_at', rtd.updated_at
                )
                ORDER BY rtd.power_level DESC, rtd.template_name
            )
            FROM role_template_details rtd
        ),
        'summary', JSON_BUILD_OBJECT(
            'total_templates', COUNT(*),
            'system_templates', COUNT(*) FILTER (WHERE is_system_template = true),
            'organization_templates', COUNT(*) FILTER (WHERE is_system_template = false),
            'current_organization', (SELECT organization_id FROM user_organization),
            'package_restrictions_applied', true
        )
    ) as templates_data
FROM role_template_details
"""

# For SINGLE template
GET_SINGLE_ROLE_TEMPLATE = """
WITH 
user_organization AS (
    SELECT organization_id FROM users WHERE id = %s
),
active_package_menus AS (
    SELECT organization_id, allowed_menu_ids
    FROM packages 
    WHERE organization_id = (SELECT organization_id FROM user_organization)
      AND status = 'active'
      AND CURRENT_DATE BETWEEN effective_date 
          AND (expiry_date + INTERVAL '1 day' * grace_period_days)
    ORDER BY created_at DESC
    LIMIT 1
),
filtered_permission_structures AS (
    SELECT DISTINCT ps.id
    FROM permission_structures ps
    CROSS JOIN active_package_menus apm
    WHERE ps.record_type = 'module'
       OR ps.id = ANY(SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer)
       OR (ps.record_type = 'card' AND ps.parent_id IN (
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       ))
)
SELECT 
    JSON_BUILD_OBJECT(
        'template', (
            SELECT JSON_BUILD_OBJECT(
                'template_key', rt.template_key,
                'template_name', rt.name,
                'description', rt.description,
                'permission_ids', rt.permission_ids,
                'power_level', rt.power_level,
                'is_system_template', rt.is_system_template,
                'created_at', rt.created_at,
                'updated_at', rt.updated_at,
                'permission_details', (
                    SELECT JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'id', p.id,
                            'action', p.permission_action,
                            'display_name', p.display_name,
                            'power_level', p.power_level,
                            'description', p.description
                        )
                    )
                    FROM permissions p
                    WHERE p.id = ANY(rt.permission_ids)
                      AND p.id IN (
                          SELECT rp.permission_id 
                          FROM role_permissions rp 
                          WHERE rp.structure_id IN (SELECT id FROM filtered_permission_structures)
                      )
                ),
                'roles_using_count', (
                    SELECT COUNT(DISTINCT r.id)
                    FROM roles r
                    WHERE r.template_id = rt.template_key 
                      AND r.is_active = true
                )
            )
            FROM role_templates rt
            WHERE rt.template_key = %s
              AND rt.is_active = true
              AND (
                  rt.is_system_template = true
                  OR EXISTS (
                      SELECT 1 FROM roles r2 
                      WHERE r2.template_id = rt.template_key 
                        AND r2.organization_id = (SELECT organization_id FROM user_organization)
                  )
              )
        )
    ) as template_data
"""

# For MULTIPLE templates
GET_MULTIPLE_ROLE_TEMPLATES = """
WITH 
user_organization AS (
    SELECT organization_id FROM users WHERE id = %s
),
active_package_menus AS (
    SELECT organization_id, allowed_menu_ids
    FROM packages 
    WHERE organization_id = (SELECT organization_id FROM user_organization)
      AND status = 'active'
      AND CURRENT_DATE BETWEEN effective_date 
          AND (expiry_date + INTERVAL '1 day' * grace_period_days)
    ORDER BY created_at DESC
    LIMIT 1
),
filtered_permission_structures AS (
    SELECT DISTINCT ps.id
    FROM permission_structures ps
    CROSS JOIN active_package_menus apm
    WHERE ps.record_type = 'module'
       OR ps.id = ANY(SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer)
       OR (ps.record_type = 'card' AND ps.parent_id IN (
           SELECT jsonb_array_elements_text(apm.allowed_menu_ids)::integer
       ))
),
requested_templates AS (
    SELECT UNNEST(%s) as template_key
),
role_template_details AS (
    SELECT 
        rt.template_key,
        rt.name as template_name,
        rt.description,
        rt.permission_ids,
        rt.power_level,
        rt.is_system_template,
        rt.created_at,
        rt.updated_at,
        (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'id', p.id,
                    'action', p.permission_action,
                    'display_name', p.display_name,
                    'power_level', p.power_level,
                    'description', p.description
                )
            )
            FROM permissions p
            WHERE p.id = ANY(rt.permission_ids)
              AND p.id IN (
                  SELECT rp.permission_id 
                  FROM role_permissions rp 
                  WHERE rp.structure_id IN (SELECT id FROM filtered_permission_structures)
              )
        ) as permission_details,
        COUNT(DISTINCT r.id) as roles_using_count
    FROM role_templates rt
    LEFT JOIN roles r ON r.template_id = rt.template_key AND r.is_active = true
    WHERE rt.is_active = true
      AND rt.template_key IN (SELECT template_key FROM requested_templates)
      AND (
          rt.is_system_template = true
          OR EXISTS (
              SELECT 1 FROM roles r2 
              WHERE r2.template_id = rt.template_key 
                AND r2.organization_id = (SELECT organization_id FROM user_organization)
          )
      )
    GROUP BY rt.template_key, rt.name, rt.description, rt.permission_ids, 
             rt.power_level, rt.is_system_template, rt.created_at, rt.updated_at
)
SELECT 
    JSON_BUILD_OBJECT(
        'templates', (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'template_key', rtd.template_key,
                    'template_name', rtd.template_name,
                    'description', rtd.description,
                    'permission_ids', rtd.permission_ids,
                    'power_level', rtd.power_level,
                    'is_system_template', rtd.is_system_template,
                    'permission_details', rtd.permission_details,
                    'roles_using_count', rtd.roles_using_count,
                    'created_at', rtd.created_at,
                    'updated_at', rtd.updated_at
                )
                ORDER BY rtd.power_level DESC, rtd.template_name
            )
            FROM role_template_details rtd
        ),
        'summary', JSON_BUILD_OBJECT(
            'total_templates', COUNT(*),
            'requested_templates', (SELECT COUNT(*) FROM requested_templates),
            'found_templates', COUNT(*),
            'current_organization', (SELECT organization_id FROM user_organization),
            'package_restrictions_applied', true
        )
    ) as templates_data
FROM role_template_details
"""

# Optional: Template usage stats
GET_TEMPLATE_USAGE_STATS_BY_KEY = """
SELECT 
    COUNT(DISTINCT r.id) as active_roles_count,
    COUNT(DISTINCT ur.user_id) as active_users_count,
    MAX(r.created_at) as last_used_at
FROM role_templates rt
LEFT JOIN roles r ON r.template_id = rt.template_key AND r.is_active = true
LEFT JOIN user_roles ur ON ur.role_id = r.role_id AND ur.organization_id = r.organization_id
WHERE rt.template_key = %s
  AND rt.is_active = true
GROUP BY rt.template_key
"""


"""
User-related SQL queries following the same pattern as permission queries.
"""

# ======================================================
# USER ORGANIZATION & ACCESS
# ======================================================

GET_USER_ORGANIZATION = """
SELECT u.org_id, o.name AS org_name, o.status AS org_status
FROM users u
JOIN organizations o ON u.org_id = o.org_id
WHERE u.user_id = %(user_id)s
"""

VERIFY_USER_ACCESS = """
SELECT user_id 
FROM users 
WHERE user_id = %(user_id)s 
  AND org_id = %(org_id)s
  AND status = 'AC'
"""

VERIFY_USER_EMAIL_EXISTS = """
SELECT user_id 
FROM users 
WHERE email = %(email)s 
  AND org_id = %(org_id)s
  AND status = 'AC'
  {exclude_clause}
"""

# ======================================================
# USER LISTING & SEARCH
# ======================================================


ORGANIZATION_USERS_QUERY = """
WITH current_org AS (
    SELECT org_id
    FROM users
    WHERE user_id = %(current_user_id)s
),
user_base AS (
    SELECT 
        u.user_id,
        u.uid,
        u.email,
        u.display_name,
        u.org_id,
        u.email_verified,
        u.created_at,
        u.updated_at,
        u.status,
        u.department,
        u.location,
        u.status_effective_from,
        u.status_effective_to
    FROM users u
    WHERE u.org_id = (SELECT org_id FROM current_org)
      AND u.status = 'AC'
),
user_roles AS (
    SELECT 
        ur.user_id,
        COALESCE(
            json_agg(ur.role_id::text ORDER BY ur.role_id),
            '[]'::json
        ) AS roles
    FROM user_roles ur
    WHERE ur.org_id = (SELECT org_id FROM current_org)
    GROUP BY ur.user_id
),
total_count AS (
    SELECT COUNT(*) AS total
    FROM user_base
),
paged_users AS (
    SELECT *
    FROM user_base u
    ORDER BY u.created_at DESC
    OFFSET %(offset)s LIMIT %(limit)s
)
SELECT json_build_object(
    'items', (
        SELECT json_agg(
            json_build_object(
                'user_id', pu.user_id,
                'uid', pu.uid,
                'email', pu.email,
                'display_name', pu.display_name,
                'org_id', pu.org_id,
                'email_verified', pu.email_verified,
                'created_at', pu.created_at,
                'updated_at', pu.updated_at,
                'status', pu.status,
                'department', pu.department,
                'location', pu.location,
                'status_effective_from', pu.status_effective_from,
                'status_effective_to', pu.status_effective_to,
                'roles', COALESCE(ur.roles, '[]'::json)
            )
        )
        FROM paged_users pu
        LEFT JOIN user_roles ur ON pu.user_id = ur.user_id
    ),
    'total', (SELECT total FROM total_count),
    'offset', %(offset)s,
    'limit', %(limit)s,
    'org_id', (SELECT org_id FROM current_org),
    'version', json_build_array(
        json_build_object(
            'table_name', 'users',
            'table_version', (
                SELECT MAX(table_version)
                FROM tableversion
                WHERE table_name = 'users'
                  AND org_id = (SELECT org_id FROM current_org)
            )
        )
    )
) AS users_data
"""

GET_USER_DETAILS = """
SELECT 
    u.user_id,
    u.uid,
    u.email,
    u.display_name,
    u.org_id,
    u.email_verified,
    u.created_at,
    u.updated_at,
    u.status,
    u.department,
    u.location,
    u.status_effective_from,
    u.status_effective_to,
    COALESCE(
        json_agg(ur.role_id::text ORDER BY ur.role_id),
        '[]'::json
    ) AS roles,
    o.name AS organization_name
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.user_id AND ur.org_id = u.org_id
JOIN organizations o ON u.org_id = o.org_id
WHERE u.user_id = %(user_id)s
  AND u.org_id = %(org_id)s
  AND u.status = 'AC'
GROUP BY u.user_id, o.name
"""

SEARCH_USERS_COUNT = """
SELECT COUNT(*) as total
FROM users u
WHERE u.org_id = %(org_id)s
  AND u.status = 'AC'
  AND (
      u.display_name ILIKE %(search_pattern)s
      OR u.email ILIKE %(search_pattern)s
      OR u.uid ILIKE %(search_pattern)s
  )
"""

SEARCH_USERS = """
SELECT 
    u.user_id,
    u.uid,
    u.email,
    u.display_name,
    u.org_id,
    u.email_verified,
    u.created_at,
    u.updated_at,
    u.status,
    u.department,
    u.location,
    COALESCE(
        json_agg(ur.role_id::text ORDER BY ur.role_id),
        '[]'::json
    ) AS roles
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.user_id AND ur.org_id = u.org_id
WHERE u.org_id = %(org_id)s
  AND u.status = 'AC'
  AND (
      u.display_name ILIKE %(search_pattern)s
      OR u.email ILIKE %(search_pattern)s
      OR u.uid ILIKE %(search_pattern)s
  )
GROUP BY u.user_id
ORDER BY u.display_name
OFFSET %(offset)s LIMIT %(limit)s
"""

# ======================================================
# USER CREATE
# ======================================================

CREATE_USER = """
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
    %(email_verified)s,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
RETURNING user_id
"""

# ======================================================
# USER UPDATE
# ======================================================

UPDATE_USER_FIELDS = """
UPDATE users 
SET {update_fields},
    updated_at = CURRENT_TIMESTAMP
WHERE user_id = %(user_id)s
  AND org_id = %(org_id)s
  AND status = 'AC'
RETURNING user_id
"""

# ======================================================
# USER DELETE
# ======================================================

SOFT_DELETE_USER = """
UPDATE users 
SET 
    status = 'DE',
    updated_at = CURRENT_TIMESTAMP
WHERE user_id = %(user_id)s
  AND org_id = %(org_id)s
  AND status != 'DE'
RETURNING user_id
"""

HARD_DELETE_USER = """
DELETE FROM users 
WHERE user_id = %(user_id)s
  AND org_id = %(org_id)s
RETURNING user_id
"""

# ======================================================
# USER ROLES MANAGEMENT
# ======================================================

DELETE_USER_ROLES = """
DELETE FROM user_roles 
WHERE user_id = %(user_id)s 
  AND org_id = %(org_id)s
"""

INSERT_USER_ROLE = """
INSERT INTO user_roles (user_id, role_id, org_id, updated_by, updated_at)
VALUES (%(user_id)s, %(role_id)s, %(org_id)s, %(assigned_by)s, CURRENT_TIMESTAMP)
ON CONFLICT (user_id, role_id, org_id) DO UPDATE 
SET updated_by = EXCLUDED.updated_by,
    updated_at = CURRENT_TIMESTAMP
"""

UPDATE_FOR_DELETE_USER = """
UPDATE user_roles 
SET 
    status = 'DE',
    updated_at = CURRENT_TIMESTAMP
    WHERE user_id = %(user_id)s
        AND org_id = %(org_id)s
          AND status != 'DE'
RETURNING user_id
"""

VERIFY_ROLE_ACCESS = """
SELECT role_id 
FROM roles 
WHERE role_id = %(role_id)s 
  AND org_id = %(org_id)s
  AND is_active = TRUE
"""

# ======================================================
# AUDIT LOGGING
# ======================================================

LOG_USER_ACTION = """
INSERT INTO permission_audit (user_id, action, performed_by, details)
VALUES (%(user_id)s, %(action)s, %(performed_by)s, %(details)s)
"""

# ======================================================
# POWER ANALYSIS
# ======================================================

GET_ROLE_POWER_ANALYSIS = """
SELECT 
    COALESCE(MAX(ad.power_level), 0) as max_power,
    COUNT(DISTINCT rp.structure_id) as permission_count
FROM role_permissions rp
JOIN permission_structures ps ON rp.structure_id = ps.permissstruct_id
CROSS JOIN LATERAL jsonb_array_elements_text(ps.allowed_actions) as action_val
JOIN action_definitions ad ON ad.action_key = action_val
WHERE rp.role_id = %(role_id)s AND rp.status = 'AC'
"""
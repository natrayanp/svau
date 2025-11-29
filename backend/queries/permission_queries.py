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
        ps.id, ps.record_type, ps.key, ps.name, ps.description,
        ps.icon, ps.color, ps.allowed_actions, 
        ps.parent_id, ps.display_order,
        NULL as parent_name,
        1 as level
    FROM permission_structures ps
    WHERE ps.record_type = 'module' AND ps.is_active = true
    
    UNION ALL
    
    SELECT 
        child.id, child.record_type, child.key, child.name, child.description,
        child.icon, child.color, child.allowed_actions,
        child.parent_id, child.display_order,
        parent.name as parent_name,
        parent.level + 1 as level
    FROM permission_structures child
    INNER JOIN recursive_structure parent ON child.parent_id = parent.id
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
    rp.role_key,
    COUNT(DISTINCT rp.structure_id) as permission_count,
    -- Check if this role has any template permissions
    BOOL_OR(rp.is_template) as has_templates,
    COUNT(DISTINCT ur.user_id) as user_count,
    -- Get template info if any
    MAX(rp.template_name) as template_name,
    MAX(rp.template_description) as template_description
FROM role_permissions rp
LEFT JOIN user_roles ur ON rp.role_key = ur.role_key
WHERE rp.is_template = false  -- Only show non-template role assignments
GROUP BY rp.role_key
ORDER BY permission_count DESC
"""



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

GET_USER_ROLE = "SELECT role_key FROM user_roles WHERE user_id = %s"

# DEFAULT PERMISSIONS QUERY
GET_DEFAULT_PERMISSIONS = "SELECT id FROM permissions WHERE power_level <= 20 AND is_active = TRUE ORDER BY power_level LIMIT 5"

#PERMISSION_STRUCTURE_QUERY
PERMISSION_STRUCTURE_QUERY = """
WITH recursive_structure AS (
    -- Get modules (level 1)
    SELECT 
        id,
        record_type,
        key,
        name,
        description,
        icon,
        color,
        display_order,
        allowed_actions,
        parent_id,
        NULL as parent_name,
        1 as level
    FROM permission_structures 
    WHERE record_type = 'module' AND is_active = true
    
    UNION ALL
    
    -- Get menus and cards (level 2+)
    SELECT 
        child.id,
        child.record_type,
        child.key,
        child.name,
        child.description,
        child.icon,
        child.color,
        child.display_order,
        child.allowed_actions,
        child.parent_id,
        parent.name as parent_name,
        parent.level + 1 as level
    FROM permission_structures child
    INNER JOIN recursive_structure parent ON child.parent_id = parent.id
    WHERE child.is_active = true
),
structure_with_actions AS (
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
),
action_details_agg AS (
    SELECT 
        id,
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'action_key', action_key,
                'display_name', action_display_name,
                'power_level', power_level,
                'category', category
            )
        ) as action_details
    FROM structure_with_actions
    GROUP BY id
),
cards_aggregated AS (
    SELECT 
        ps.id,
        ps.parent_id as menu_id,
        JSON_BUILD_OBJECT(
            'id', ps.id::text,
            'record_type', ps.record_type,
            'key', ps.key,
            'name', ps.name,
            'description', ps.description,
            'display_order', ps.display_order,
            'menu_id', ps.parent_id::text,
            'allowed_actions', COALESCE(ada.action_details, '[]'::json)
        ) as card_data
    FROM permission_structures ps
    LEFT JOIN action_details_agg ada ON ps.id = ada.id
    WHERE ps.record_type = 'card' AND ps.is_active = true
),
menus_with_cards AS (
    SELECT 
        ps.id,
        ps.parent_id as module_id,
        JSON_BUILD_OBJECT(
            'id', ps.id::text,
            'record_type', ps.record_type,
            'key', ps.key,
            'name', ps.name,
            'description', ps.description,
            'display_order', ps.display_order,
            'module_id', ps.parent_id::text,
            'allowed_actions', COALESCE(ada.action_details, '[]'::json),
            'cards', COALESCE(
                (SELECT JSON_AGG(card_data ORDER BY (card_data->>'display_order')::int)
                 FROM cards_aggregated ca 
                 WHERE ca.menu_id = ps.id),
                '[]'::json
            )
        ) as menu_data
    FROM permission_structures ps
    LEFT JOIN action_details_agg ada ON ps.id = ada.id
    WHERE ps.record_type = 'menu' AND ps.is_active = true
),
modules_with_menus AS (
    SELECT 
        ps.id,
        JSON_BUILD_OBJECT(
            'id', ps.id::text,
            'record_type', ps.record_type,
            'key', ps.key,
            'name', ps.name,
            'description', ps.description,
            'icon', ps.icon,
            'color', ps.color,
            'display_order', ps.display_order,
            'allowed_actions', COALESCE(ada.action_details, '[]'::json),
            'menus', COALESCE(
                (SELECT JSON_AGG(menu_data ORDER BY (menu_data->>'display_order')::int)
                 FROM menus_with_cards mwc 
                 WHERE mwc.module_id = ps.id),
                '[]'::json
            )
        ) as module_data
    FROM permission_structures ps
    LEFT JOIN action_details_agg ada ON ps.id = ada.id
    WHERE ps.record_type = 'module' AND ps.is_active = true
)
SELECT 
    JSON_BUILD_OBJECT(
        'modules', (
            SELECT JSON_AGG(module_data ORDER BY (module_data->>'display_order')::int)
            FROM modules_with_menus
        ),
        'metadata', JSON_BUILD_OBJECT(
            'total_modules', (SELECT COUNT(*) FROM permission_structures WHERE record_type = 'module' AND is_active = true),
            'total_menus', (SELECT COUNT(*) FROM permission_structures WHERE record_type = 'menu' AND is_active = true),
            'total_cards', (SELECT COUNT(*) FROM permission_structures WHERE record_type = 'card' AND is_active = true),
            'total_permissions', (
                SELECT COUNT(*)
                FROM permission_structures ps
                CROSS JOIN LATERAL jsonb_array_elements_text(ps.allowed_actions) as action_val
                WHERE ps.is_active = true
            ),
            'last_updated', NOW()::text
        )
    ) as permission_structure
"""


ORGANIZATION_ROLES_QUERY = """
WITH user_organization AS (
    SELECT organization_id 
    FROM users 
    WHERE id = :current_user_id  -- 👈 CURRENT USER CONTEXT
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
role_permission_counts AS (
    SELECT 
        r.role_key,
        r.organization_id,
        COUNT(DISTINCT rp.id) as permission_count,
        JSON_AGG(DISTINCT rp.id) as permission_ids
    FROM roles r
    CROSS JOIN LATERAL jsonb_array_elements_text(r.permission_ids) as perm_id
    JOIN role_permissions rp ON rp.id = perm_id::integer
    JOIN permission_structures ps ON rp.structure_id = ps.id
    WHERE r.is_active = true 
      AND rp.is_active = true
      AND ps.id IN (SELECT id FROM filtered_permission_structures)  -- 👈 PACKAGE FILTER
      AND r.organization_id = (SELECT organization_id FROM user_organization)  -- 👈 ORG FILTER
    GROUP BY r.role_key, r.organization_id
),
role_user_counts AS (
    SELECT 
        ur.role_key,
        ur.organization_id,
        COUNT(DISTINCT ur.user_id) as user_count
    FROM user_roles ur
    JOIN users u ON ur.user_id = u.id
    WHERE u.is_active = true
      AND ur.organization_id = (SELECT organization_id FROM user_organization)  -- 👈 ORG FILTER
    GROUP BY ur.role_key, ur.organization_id
),
role_details AS (
    SELECT 
        r.role_key,
        r.organization_id,
        r.display_name,
        r.description,
        r.is_system_role,
        r.is_template,
        r.template_id,
        r.template_name,
        r.created_at,
        o.name as organization_name,
        COALESCE(rpc.permission_count, 0) as permission_count,
        COALESCE(rpc.permission_ids, '[]'::jsonb) as permission_ids,
        COALESCE(ruc.user_count, 0) as user_count
    FROM roles r
    JOIN organizations o ON r.organization_id = o.id
    LEFT JOIN role_permission_counts rpc ON r.role_key = rpc.role_key AND r.organization_id = rpc.organization_id
    LEFT JOIN role_user_counts ruc ON r.role_key = ruc.role_key AND r.organization_id = ruc.organization_id
    WHERE r.is_active = true
      AND r.organization_id = (SELECT organization_id FROM user_organization)  -- 👈 ORG FILTER
)
SELECT 
    JSON_BUILD_OBJECT(
        'roles', (
            SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'role_key', rd.role_key,
                    'organization_id', rd.organization_id,
                    'display_name', rd.display_name,
                    'description', rd.description,
                    'is_system_role', rd.is_system_role,
                    'is_template', rd.is_template,
                    'template_id', rd.template_id,
                    'template_name', rd.template_name,
                    'organization_name', rd.organization_name,
                    'permission_count', rd.permission_count,
                    'permission_ids', rd.permission_ids,
                    'user_count', rd.user_count,
                    'created_at', rd.created_at
                )
                ORDER BY rd.display_name
            )
            FROM role_details rd
        ),
        'summary', JSON_BUILD_OBJECT(
            'total_roles', COUNT(*),
            'system_roles', COUNT(*) FILTER (WHERE is_system_role = true),
            'template_roles', COUNT(*) FILTER (WHERE is_template = true),
            'custom_roles', COUNT(*) FILTER (WHERE is_system_role = false AND is_template = false),
            'total_permission_assignments', SUM(permission_count),
            'total_user_assignments', SUM(user_count),
            'current_organization', (SELECT organization_id FROM user_organization),
            'package_restrictions_applied', true  -- 👈 INDICATES FILTERING
        )
    ) as roles_data
FROM role_details
"""

ORGANIZATION_USERS_QUERY="""
WITH requester_org AS (
    SELECT organization_id
    FROM users
    WHERE id = $1
)
SELECT 
    u.id,
    u.uid,
    u.email,
    u.display_name,
    u.organization_id,
    u.email_verified,
    u.created_at,
    u.updated_at,
    COALESCE(
      json_agg(r.role_key) FILTER (WHERE r.role_key IS NOT NULL),
      '[]'
    ) AS roles
FROM users u
JOIN requester_org ro ON u.organization_id = ro.organization_id
JOIN organizations o ON u.organization_id = o.id
LEFT JOIN user_roles ur 
  ON u.id = ur.user_id AND u.organization_id = ur.organization_id
LEFT JOIN roles r 
  ON ur.role_key = r.role_key AND ur.organization_id = r.organization_id
WHERE o.is_active = TRUE
GROUP BY u.id, u.uid, u.email, u.display_name, u.organization_id, u.email_verified, u.created_at, u.updated_at;
"""

















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
LEFT JOIN user_roles ur ON ur.role_key = r.role_key AND ur.organization_id = r.organization_id
WHERE rt.template_key = %s
  AND rt.is_active = true
GROUP BY rt.template_key
"""
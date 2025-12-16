"""
Optimized authentication queries - ID-based permissions with power support
"""

# Create organization and return its id
CREATE_ORGANIZATION_QRY="""
INSERT INTO organizations (
    name,
    slug,
    status,
    created_by,
    created_at,
    updated_at
) VALUES (
    %(name)s, %(slug)s, %(status)s, %(created_by)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
RETURNING org_id
"""


GET_SYSTEM_ROLES_FOR_CLONING = """
SELECT 
    role_id,
    display_name,
    description,
    is_template,
    template_id,
    template_name,
    template_description,
    template_category
FROM roles
WHERE is_system_role = TRUE
AND org_id = 0 """

GET_SYSTEM_ENTITIES = "SELECT entity_name, entity_id FROM system_entities"

GET_SYSTEM_ROLES_WITH_PERMISSIONS = """
SELECT
    r.role_id,
    r.display_name,
    r.description,
    r.is_system_role,
    COALESCE(
        json_agg(
            json_build_object(
                'permissstruct_id', rp.structure_id,
                'granted_action_key', rp.granted_actions
            )
        ) FILTER (WHERE rp.role_id IS NOT NULL),
        '[]'
    ) AS permissions
FROM roles r
LEFT JOIN role_permissions rp ON rp.role_id = r.role_id
WHERE r.org_id = %(org_id)s AND r.is_system_role = TRUE
GROUP BY r.role_id, r.display_name, r.description, r.is_system_role
"""



"""CLONE_SYSTEM_ROLE_PERMISSIONS=
INSERT INTO role_permissions (
    role_id,
    structure_id,
    granted_actions,
    status,
    created_at,
    updated_at
)
SELECT
    %(new_role_id)s,
    rp.structure_id,
    rp.granted_actions,
    'AC',
    NOW(),
    NOW()
FROM role_permissions rp
WHERE rp.role_id = %(old_role_id)s
ON CONFLICT (role_id, structure_id)
DO UPDATE SET
    granted_actions = EXCLUDED.granted_actions,
    updated_at = NOW()
"""


GET_USER_BY_UID = "SELECT * FROM users WHERE uid = %(uid)s"
GET_USER_BY_EMAIL = "SELECT * FROM users WHERE email = %(email)s"
GET_ORG_ID = "SELECT org_id FROM organizations WHERE org_id = %(org_id)s AND status NOT IN ('IA', 'SU', 'EX', 'CA', 'DE')"
GET_USER_BY_ID = "SELECT * FROM users WHERE id = %(user_id)s AND status NOT IN ('IA', 'SU', 'EX', 'CA', 'DE')"
UPDATE_USER = "UPDATE users SET display_name = %(display_name)s, role = %(role)s, email_verified = %(email_verified)s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %(user_id)s"

#--------------/structure-------------------------#
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

"""GET_SYSTEM_ROLES=
SELECT role_id, display_name, description, permissions
FROM roles
WHERE is_system_role = TRUE
"""

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


GET_ORGANIZATION_BY_ID="""
SELECT 
    org_id,
    name,
    slug,
    status,
    created_at,
    updated_at
FROM organizations
WHERE org_id = %(org_id)s
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
INSERT INTO roles (org_id, display_name, description, is_system_role, is_template, created_by,created_at,updated_at)
VALUES (%(org_id)s, %(display_name)s, %(description)s, FALSE, FALSE, %(created_by)s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
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
RETURNING *
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
INSERT INTO user_roles (user_id, role_id, org_id, created_by,updated_by, created_at,updated_at)
VALUES (%(user_id)s, %(role_id)s, %(org_id)s, %(assigned_by)s, %(assigned_by)s, CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
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
WHERE role_id = ANY(%(role_ids)s)
  AND org_id = %(org_id)s
  AND is_active = TRUE
"""

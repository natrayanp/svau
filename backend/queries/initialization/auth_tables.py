"""
Optimized authentication tables - ID-based permissions only
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uid VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'basic' CHECK (role IN ('basic', 'creator', 'moderator', 'admin')),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USER_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL,
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, permission_id)
);
"""

CREATE_PERMISSION_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS permission_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('GRANT', 'REVOKE')),
    performed_by INTEGER NOT NULL REFERENCES users(id),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_permission_audit_user_id ON permission_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_permission_audit_permission_id ON permission_audit(permission_id);
"""

TABLES = {
    'users': CREATE_USERS_TABLE,
    'user_permissions': CREATE_USER_PERMISSIONS_TABLE,
    'permission_audit': CREATE_PERMISSION_AUDIT_TABLE
}
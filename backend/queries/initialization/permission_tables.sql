-- =============================================
-- COMPLETE CORRECTED SCHEMA (PostgreSQL)
-- =============================================

-- Allowed status values: AC=active, IA=in-active, SU=suspended, EX=expired, CA=cancelled, DE=deleted
-- Note: 'user_id' is a single primary key for users to allow direct foreign keys elsewhere.

CREATE TABLE organizations (
    org_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'IA',
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    uid VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    org_id INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE RESTRICT,
    role_id INTEGER NOT NULL REFERENCES roles(role_id),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'IA',    
    UNIQUE(org_id, email),
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);

CREATE TABLE packages (
    package_id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    package_name VARCHAR(200) NOT NULL,
    package_key VARCHAR(100) NOT NULL,
    description TEXT,
    allowed_menu_ids JSONB NOT NULL DEFAULT '[]',
    max_users INTEGER DEFAULT 10,
    max_storage_mb INTEGER DEFAULT 1024,
    features JSONB DEFAULT '{}',
    price_monthly DECIMAL(10,2) DEFAULT 0.00,
    price_yearly DECIMAL(10,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    effective_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    grace_period_days INTEGER DEFAULT 7,
    is_trial BOOLEAN DEFAULT FALSE,
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'IA',
    CHECK (expiry_date >= effective_date),
    CHECK (grace_period_days >= 0),
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);

CREATE TABLE action_definitions (
    action_key VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    power_level INTEGER NOT NULL CHECK (power_level BETWEEN 1 AND 100),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'IA',
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);

CREATE TABLE permission_structures (
    permissstruct_id SERIAL PRIMARY KEY,
    record_type VARCHAR(20) NOT NULL CHECK (record_type IN ('module', 'menu', 'card')),
    key VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    icon VARCHAR(50),
    color VARCHAR(20),
    parent_id INTEGER REFERENCES permission_structures(permissstruct_id) ON DELETE SET NULL,
    allowed_actions JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'IA',
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);


create table role_permissions_legacy as select * from role_permissions
create table roles_legacy as select * from roles


CREATE TABLE role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    structure_id INTEGER NOT NULL REFERENCES permission_structures(permissstruct_id) ON DELETE CASCADE,
    granted_actions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'IA',
    UNIQUE (role_id,structure_id),
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);

CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_template BOOLEAN DEFAULT FALSE,
    template_id VARCHAR(100),
    template_name VARCHAR(200),
    template_description TEXT,
    template_category VARCHAR(50),
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'IA',
    CONSTRAINT template_check CHECK (
        (is_template = true AND template_id IS NOT NULL AND template_name IS NOT NULL)
        OR
        (is_template = false AND template_id IS NULL)
    ),
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);

CREATE TABLE user_roles (
    userrole_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    org_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'IA',
    UNIQUE(user_id, role_id, org_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (status IN ('AC', 'IA', 'SU', 'EX', 'CA', 'DE'))
);



CREATE TABLE TableVersion (
    table_name     TEXT        NOT NULL,  -- Name of the source table
    table_version  INT         NOT NULL,  -- Global version number for that table/org
    org_id         INT         NOT NULL,  -- Organization identifier

    PRIMARY KEY (table_name, org_id)      -- Ensures uniqueness per table/org
);

-- Function called by all triggers for table version
CREATE OR REPLACE FUNCTION bump_table_version_statement()
RETURNS trigger AS $$
BEGIN
    INSERT INTO TableVersion (table_name, table_version, org_id)
    SELECT TG_TABLE_NAME, 1, org_id
    FROM new_rows
    ON CONFLICT (table_name, org_id)
    DO UPDATE SET table_version = TableVersion.table_version + 1;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


--PL/pgSQL Script for Auto‑Generating Triggers
CREATE TRIGGER trg_users_version_insert
AFTER INSERT ON users
REFERENCING NEW TABLE AS new_rows
FOR EACH STATEMENT
EXECUTE FUNCTION bump_table_version_statement();

CREATE TRIGGER trg_users_version_update
AFTER UPDATE ON users
REFERENCING NEW TABLE AS new_rows
FOR EACH STATEMENT
EXECUTE FUNCTION bump_table_version_statement();

-- Optional: a convenience index to speed lookups
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_packages_org_id ON packages(org_id);
CREATE INDEX idx_roles_org_id ON roles(org_id);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_permission_structures_key ON permission_structures(key);


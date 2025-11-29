-- =============================================
-- COMPLETE CORRECTED SCHEMA
-- =============================================

CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL,
    uid VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, organization_id),
    UNIQUE(organization_id, email)
);

CREATE TABLE packages (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
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
    status VARCHAR(20) DEFAULT 'active',
    is_trial BOOLEAN DEFAULT FALSE,
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    CHECK (expiry_date >= effective_date),
    CHECK (grace_period_days >= 0),
    CHECK (status IN ('active', 'suspended', 'expired', 'cancelled'))
);

CREATE TABLE action_definitions (
    action_key VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    power_level INTEGER NOT NULL CHECK (power_level BETWEEN 1 AND 100),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permission_structures (
    id SERIAL PRIMARY KEY,
    record_type VARCHAR(20) NOT NULL CHECK (record_type IN ('module', 'menu', 'card')),
    key VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    icon VARCHAR(50),
    color VARCHAR(20),
    parent_id INTEGER REFERENCES permission_structures(id),
    module_id INTEGER,
    menu_id INTEGER,
    allowed_actions JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    structure_id INTEGER NOT NULL REFERENCES permission_structures(id),
    granted_actions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(structure_id, granted_actions)
);

CREATE TABLE roles (
    role_key VARCHAR(50) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permission_ids JSONB NOT NULL DEFAULT '[]',
    is_template BOOLEAN DEFAULT FALSE,
    template_id VARCHAR(100),
    template_name VARCHAR(200),
    template_description TEXT,
    template_category VARCHAR(50),
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    PRIMARY KEY (role_key, organization_id),
    CONSTRAINT template_check CHECK (
        (is_template = true AND template_id IS NOT NULL AND template_name IS NOT NULL) OR
        (is_template = false AND template_id IS NULL)
    )
);

CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role_key VARCHAR(50) NOT NULL,
    organization_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, role_key),
    FOREIGN KEY (role_key, organization_id) REFERENCES roles(role_key, organization_id),
    FOREIGN KEY (user_id, organization_id) REFERENCES users(id, organization_id)
);
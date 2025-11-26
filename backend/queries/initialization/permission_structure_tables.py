"""
Enhanced permission structure tables for power-based system - OPTIMIZED FOR NUMBER IDs
"""

CREATE_PERMISSION_MODULES_TABLE = """
CREATE TABLE IF NOT EXISTS permission_modules (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(20),
    color VARCHAR(20),
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PERMISSION_MENUS_TABLE = """
CREATE TABLE IF NOT EXISTS permission_menus (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES permission_modules(id),
    key VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, key)
);
"""

CREATE_PERMISSION_CARDS_TABLE = """
CREATE TABLE IF NOT EXISTS permission_cards (
    id SERIAL PRIMARY KEY,
    menu_id INTEGER NOT NULL REFERENCES permission_menus(id),
    key VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(menu_id, key)
);
"""

# SINGLE PERMISSIONS TABLE WITH UNIQUE NUMBER IDs
CREATE_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    permission_key VARCHAR(100) UNIQUE NOT NULL,
    permission_action VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    power_level INTEGER NOT NULL DEFAULT 10,
    default_roles JSONB DEFAULT '[]',
    module_id INTEGER REFERENCES permission_modules(id),
    menu_id INTEGER REFERENCES permission_menus(id),
    card_id INTEGER REFERENCES permission_cards(id),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_context CHECK (
        (module_id IS NOT NULL AND menu_id IS NULL AND card_id IS NULL) OR
        (module_id IS NOT NULL AND menu_id IS NOT NULL AND card_id IS NULL) OR
        (module_id IS NOT NULL AND menu_id IS NOT NULL AND card_id IS NOT NULL)
    )
);
"""

CREATE_ROLE_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_key VARCHAR(50) NOT NULL,
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    UNIQUE(role_key, permission_id)
);
"""

CREATE_USER_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, permission_id)
);
"""

CREATE_PERMISSION_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS permission_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    permission_id INTEGER REFERENCES permissions(id),
    action VARCHAR(50) NOT NULL,
    performed_by INTEGER REFERENCES users(id),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PERMISSION_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS permission_cache (
    cache_key VARCHAR(100) PRIMARY KEY,
    cache_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_permission_menus_module_id ON permission_menus(module_id);
CREATE INDEX IF NOT EXISTS idx_permission_cards_menu_id ON permission_cards(menu_id);
CREATE INDEX IF NOT EXISTS idx_permissions_power_level ON permissions(power_level);
CREATE INDEX IF NOT EXISTS idx_permissions_module_id ON permissions(module_id);
CREATE INDEX IF NOT EXISTS idx_permissions_menu_id ON permissions(menu_id);
CREATE INDEX IF NOT EXISTS idx_permissions_card_id ON permissions(card_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_key ON role_permissions(role_key);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_permission_audit_user_id ON permission_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_permission_audit_performed_at ON permission_audit(performed_at);
CREATE INDEX IF NOT EXISTS idx_permission_cache_expires ON permission_cache(expires_at);
"""

TABLES = {
    'permission_modules': CREATE_PERMISSION_MODULES_TABLE,
    'permission_menus': CREATE_PERMISSION_MENUS_TABLE,
    'permission_cards': CREATE_PERMISSION_CARDS_TABLE,
    'permissions': CREATE_PERMISSIONS_TABLE,
    'role_permissions': CREATE_ROLE_PERMISSIONS_TABLE,
    'user_permissions': CREATE_USER_PERMISSIONS_TABLE,
    'permission_audit': CREATE_PERMISSION_AUDIT_TABLE,
    'permission_cache': CREATE_PERMISSION_CACHE_TABLE
}

# SAMPLE DATA FOR POWER-BASED SYSTEM
SAMPLE_PERMISSION_DATA = [
    # Flashcards module
    ("INSERT INTO permission_modules (key, name, icon, color, description, display_order) VALUES ('flashcards', 'Flashcards', '📚', 'blue', 'Flashcard management system', 1) ON CONFLICT (key) DO NOTHING;",),
    
    # Portfolio module  
    ("INSERT INTO permission_modules (key, name, icon, color, description, display_order) VALUES ('portfolio', 'Portfolio', '💼', 'green', 'Project portfolio management', 2) ON CONFLICT (key) DO NOTHING;",),
    
    # Users module
    ("INSERT INTO permission_modules (key, name, icon, color, description, display_order) VALUES ('users', 'Users', '👥', 'purple', 'User management system', 3) ON CONFLICT (key) DO NOTHING;",),
    
    # Admin module
    ("INSERT INTO permission_modules (key, name, icon, color, description, display_order) VALUES ('admin', 'Admin', '⚙️', 'orange', 'Administration panel', 4) ON CONFLICT (key) DO NOTHING;",),
]

# Migration will handle the full structure import
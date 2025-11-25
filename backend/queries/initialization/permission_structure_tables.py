"""
Enhanced permission structure tables for power-based system
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    UNIQUE(menu_id, key)
);
"""

CREATE_CARD_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS card_permissions (
    id SERIAL PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES permission_cards(id),
    permission_action VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    power_level INTEGER NOT NULL DEFAULT 10,
    default_roles JSONB DEFAULT '[]',
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, permission_action)
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_permission_menus_module_id ON permission_menus(module_id);
CREATE INDEX IF NOT EXISTS idx_permission_cards_menu_id ON permission_cards(menu_id);
CREATE INDEX IF NOT EXISTS idx_card_permissions_card_id ON card_permissions(card_id);
CREATE INDEX IF NOT EXISTS idx_card_permissions_power_level ON card_permissions(power_level);
"""

TABLES = {
    'permission_modules': CREATE_PERMISSION_MODULES_TABLE,
    'permission_menus': CREATE_PERMISSION_MENUS_TABLE,
    'permission_cards': CREATE_PERMISSION_CARDS_TABLE,
    'card_permissions': CREATE_CARD_PERMISSIONS_TABLE
}

# SAMPLE DATA FOR POWER-BASED SYSTEM
SAMPLE_PERMISSION_DATA = [
    # Flashcards module
    ("INSERT INTO permission_modules (key, name, icon, color, description, display_order) VALUES ('flashcards', 'Flashcards', '📚', 'blue', 'Flashcard management system', 1) ON CONFLICT (key) DO NOTHING;",),
    
    # Portfolio module  
    ("INSERT INTO permission_modules (key, name, icon, color, description, display_order) VALUES ('portfolio', 'Portfolio', '💼', 'green', 'Project portfolio management', 2) ON CONFLICT (key) DO NOTHING;",),
    
    # Sample card permissions with power levels
    ("INSERT INTO card_permissions (card_id, permission_action, display_name, description, power_level, default_roles) VALUES (1001, 'view', 'View', 'View overview dashboard', 10, '[\"basic\", \"creator\", \"moderator\", \"admin\"]') ON CONFLICT DO NOTHING;",),
    ("INSERT INTO card_permissions (card_id, permission_action, display_name, description, power_level, default_roles) VALUES (1001, 'analytics', 'Analytics', 'Access analytics data', 15, '[\"creator\", \"moderator\", \"admin\"]') ON CONFLICT DO NOTHING;",),
    ("INSERT INTO card_permissions (card_id, permission_action, display_name, description, power_level, default_roles) VALUES (1003, 'delete', 'Delete', 'Delete cards', 60, '[\"moderator\", \"admin\"]') ON CONFLICT DO NOTHING;",),
]
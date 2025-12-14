"""
Migration script to convert hardcoded permission structure to database - OPTION 1
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.database.database import DatabaseManager
from utils.auth.permissions import PERMISSION_STRUCTURE

def migrate_permission_structure():
    """Migrate hardcoded permission structure to database tables"""
    db = DatabaseManager()
    
    try:
        print("Starting permission structure migration...")
        
        # Clear existing data (in correct order to handle foreign keys)
        db.execute("TRUNCATE TABLE permission_cache CASCADE")
        db.execute("TRUNCATE TABLE role_permissions CASCADE")
        db.execute("TRUNCATE TABLE card_permissions CASCADE")
        db.execute("TRUNCATE TABLE permission_cards CASCADE")
        db.execute("TRUNCATE TABLE permission_menus CASCADE")
        db.execute("TRUNCATE TABLE permission_modules CASCADE")
        
        print("Cleared existing permission data")
        
        # Insert modules
        for module in PERMISSION_STRUCTURE["modules"]:
            db.execute_insert(
                """INSERT INTO permission_modules (id, key, name, icon, color, description, display_order) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (module["id"], module["key"], module["name"], module["icon"], 
                 module["color"], module["description"], module["display_order"])
            )
            print(f"Inserted module: {module['name']}")
            
            # Insert menus
            for menu in module["menus"]:
                db.execute_insert(
                    """INSERT INTO permission_menus (id, module_id, key, name, description, display_order) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (menu["id"], module["id"], menu["key"], menu["name"], 
                     menu["description"], menu["display_order"])
                )
                print(f"  Inserted menu: {menu['name']}")
                
                # Insert cards
                for card in menu["cards"]:
                    db.execute_insert(
                        """INSERT INTO permission_cards (id, menu_id, key, name, description, display_order) 
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (card["id"], menu["id"], card["key"], card["name"], 
                         card["description"], card["display_order"])
                    )
                    print(f"    Inserted card: {card['name']}")
                    
                    # Insert permissions
                    for permission in card["permissions"]:
                        db.execute(
                            """INSERT INTO card_permissions (id, card_id, permission_action, display_name, description, power_level, default_roles) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (permission["id"], card["id"], permission["action"], 
                             permission["display_name"], permission["description"], 
                             permission["power_level"], json.dumps(permission["default_roles"]))
                        )
                        print(f"      Inserted permission: {permission['display_name']} (ID: {permission['id']})")
        
        # Migrate role permissions from hardcoded structure
        print("Migrating role permissions...")
        from utils.auth.permissions import RolePermissions
        
        role_permission_mapping = {
            "basic": {5001, 5004, 6001, 7001},
            "creator": {5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 6001, 6002, 6003, 7001, 7002},
            "moderator": {5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 6001, 6002, 6003, 6004, 8001, 8002, 7001, 7002},
            "admin": {5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010, 5011, 6001, 6002, 6003, 6004, 6005, 8001, 8002, 8003, 9001, 7001, 7002}
        }
        
        for role, permission_ids in role_permission_mapping.items():
            for perm_id in permission_ids:
                # Verify permission exists before inserting
                permission_exists = db.fetch_one(
                    "SELECT id FROM card_permissions WHERE id = %s",
                    (perm_id,)
                )

                if permission_exists:
                    db.execute(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s)",
                        (role, perm_id)
                    )
                else:
                    print(f"Warning: Permission ID {perm_id} not found for role {role}")

            print(f"Migrated {len(permission_ids)} permissions for role: {role}")
        
        # Verify migration
        print("\nVerifying migration...")

        # Count records
        modules_count = db.fetch_one("SELECT COUNT(*) as count FROM permission_modules")['count']
        menus_count = db.fetch_one("SELECT COUNT(*) as count FROM permission_menus")['count']
        cards_count = db.fetch_one("SELECT COUNT(*) as count FROM permission_cards")['count']
        permissions_count = db.fetch_one("SELECT COUNT(*) as count FROM card_permissions")['count']
        role_perms_count = db.fetch_one("SELECT COUNT(*) as count FROM role_permissions")['count']

        print(f"Migration completed successfully!")
        print(f"Modules: {modules_count}")
        print(f"Menus: {menus_count}")
        print(f"Cards: {cards_count}")
        print(f"Permissions: {permissions_count}")
        print(f"Role permissions: {role_perms_count}")
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_permission_structure()
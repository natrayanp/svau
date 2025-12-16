from fastapi import Depends
from pydantic import BaseModel
from utils.database.database import get_db

# -----------------------------
#  Model
# -----------------------------
class SystemEntities(BaseModel):
    system_org: int
    system_user: int
    admin_role: int
    system_role: int


# -----------------------------
#  Loader (DB → Model)
# -----------------------------
async def _load_system_entities(db) -> SystemEntities:
    rows = await db.fetch_all_async("""
        SELECT entity_name, entity_id
        FROM system_entities
    """)

    mapping = {row["entity_name"]: row["entity_id"] for row in rows}

    # Ensure required entities exist
    required = ["system_org", "system_user", "system_admin_role", "system_role"]
    for r in required:
        if r not in mapping:
            raise RuntimeError(f"Missing required system entity: {r}")

    return SystemEntities(
        system_org=mapping["system_org"],
        system_user=mapping["system_user"],
        admin_role=mapping["system_admin_role"],
        system_role=mapping["system_role"],
    )


# -----------------------------
#  Cached Dependency
# -----------------------------
_cached_entities: SystemEntities | None = None

async def get_system_entities(db=Depends(get_db)) -> SystemEntities:
    global _cached_entities
    if _cached_entities is None:
        _cached_entities = await _load_system_entities(db)
    return _cached_entities

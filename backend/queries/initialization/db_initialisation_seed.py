import asyncio
import asyncpg

async def seed_system_entities():
    conn = await asyncpg.connect(
        user="portfoliouser",
        password="portfoliopass",
        database="portfolio_db",
        host="db",
        port=5432,
    )

    try:
        async with conn.transaction():

            # -----------------------------
            # 1️⃣ System Organization
            # -----------------------------
            system_org = await conn.fetchrow(
                "SELECT org_id FROM organizations WHERE slug = $1",
                "system-org"
            )

            if not system_org:
                system_org = await conn.fetchrow("""
                    INSERT INTO organizations (name, slug, status, created_by)
                    VALUES ($1, $2, 'AC', NULL)
                    RETURNING org_id
                """, "System Organization", "system-org")

            system_org_id = system_org["org_id"]

            # -----------------------------
            # 2️⃣ System Admin Role (org-scoped)
            # -----------------------------
            admin_role = await conn.fetchrow("""
                SELECT role_id
                FROM roles
                WHERE org_id = $1
                  AND display_name = $2
                  AND is_system_role = TRUE
            """, system_org_id, "Admin")

            if not admin_role:
                admin_role = await conn.fetchrow("""
                    INSERT INTO roles (
                        org_id,
                        display_name,
                        description,
                        is_system_role,
                        is_active,
                        status
                    )
                    VALUES ($1, $2, $3, TRUE, TRUE, 'AC')
                    RETURNING role_id
                """, system_org_id, "Admin", "System administrator role")

            admin_role_id = admin_role["role_id"]

            # -----------------------------
            # 3️⃣ System User
            # -----------------------------
            system_user = await conn.fetchrow(
                "SELECT user_id FROM users WHERE uid = $1",
                "system_user"
            )

            if not system_user:
                system_user = await conn.fetchrow("""
                    INSERT INTO users (
                        uid,
                        email,
                        display_name,
                        org_id,
                        role_id,
                        email_verified,
                        status
                    )
                    VALUES ($1, $2, $3, $4, $5, TRUE, 'AC')
                    RETURNING user_id
                """,
                    "system_user",
                    "system@example.com",
                    "System User",
                    system_org_id,
                    admin_role_id
                )

            system_user_id = system_user["user_id"]

            # -----------------------------
            # 4️⃣ Default System Role
            # -----------------------------
            system_role = await conn.fetchrow("""
                SELECT role_id
                FROM roles
                WHERE org_id = $1
                  AND display_name = $2
                  AND is_system_role = TRUE
            """, system_org_id, "System Role")

            if not system_role:
                system_role = await conn.fetchrow("""
                    INSERT INTO roles (
                        org_id,
                        display_name,
                        description,
                        is_system_role,
                        is_active,
                        status
                    )
                    VALUES ($1, $2, $3, TRUE, TRUE, 'AC')
                    RETURNING role_id
                """, system_org_id, "System Role", "Default system role")

            system_role_id = system_role["role_id"]

            # -----------------------------
            # 5️⃣ Insert into system_entities table
            # -----------------------------
            entities = [
                ("system_org", system_org_id, "organization", "System organization for bootstrap"),
                ("system_admin_role", admin_role_id, "role", "System admin role"),
                ("system_user", system_user_id, "user", "System user for self-registration"),
                ("system_role", system_role_id, "role", "Default system role"),
            ]

            for name, entity_id, entity_type, description in entities:
                exists = await conn.fetchval(
                    "SELECT 1 FROM system_entities WHERE entity_name = $1",
                    name
                )

                if not exists:
                    await conn.execute("""
                        INSERT INTO system_entities (
                            entity_name,
                            entity_id,
                            entity_type,
                            description
                        )
                        VALUES ($1, $2, $3, $4)
                    """, name, entity_id, entity_type, description)

        print("✅ System entities seeded successfully")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_system_entities())

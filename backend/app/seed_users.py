"""
Seed script — Creates a demo user and an admin user if they don't exist.

Run with:  python -m app.seed_users
Or during development: python app/seed_users.py

The admin user's email matches ADMIN_EMAILS in config so the admin
dashboard is accessible.
"""

import asyncio
import logging
import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_USERS = [
    {
        "email": "demo@example.com",
        "password": "demo123456",
        "name": "Demo User",
    },
    {
        "email": "admin@financialedapp.com",
        "password": "Admin123!",
        "name": "Admin User",
    },
]


async def seed():
    from app.db.session import AuthSessionLocal, DataSessionLocal
    from app.core.security import hash_password
    from sqlalchemy import text

    for user_data in SEED_USERS:
        async with AuthSessionLocal() as auth_db:
            # Check if user already exists
            result = await auth_db.execute(
                text("SELECT id FROM users WHERE lower(email) = lower(:email)"),
                {"email": user_data["email"]},
            )
            existing = result.fetchone()

            if existing:
                logger.info("User %s already exists — skipping", user_data["email"])
                continue

            hashed = hash_password(user_data["password"])
            result = await auth_db.execute(
                text(
                    """
                    INSERT INTO users (email, password_hash, is_active, is_verified)
                    VALUES (:email, :password_hash, true, true)
                    RETURNING id
                    """
                ),
                {"email": user_data["email"], "password_hash": hashed},
            )
            user_row = result.fetchone()
            user_id = user_row[0]
            await auth_db.commit()
            logger.info("Created auth user %s (id=%s)", user_data["email"], user_id)

        # Create user_profile in data DB
        async with DataSessionLocal() as data_db:
            result = await data_db.execute(
                text("SELECT user_id FROM user_profiles WHERE user_id = :uid"),
                {"uid": user_id},
            )
            if result.fetchone():
                logger.info("Profile for %s already exists", user_data["email"])
            else:
                name_parts = user_data.get("name", "").split(" ", 1)
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                await data_db.execute(
                    text(
                        """
                        INSERT INTO user_profiles (user_id, first_name, last_name)
                        VALUES (:uid, :first, :last)
                        """
                    ),
                    {"uid": user_id, "first": first_name, "last": last_name},
                )
                await data_db.commit()
                logger.info("Created data profile for %s", user_data["email"])

    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())

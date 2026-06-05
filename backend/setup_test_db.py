#!/usr/bin/env python3
"""Script to set up test databases."""

import asyncio
import asyncpg
from app.config import settings

async def setup_test_databases():
    """Create test databases if they don't exist."""
    
    # Connection to default postgres database
    conn = await asyncpg.connect(
        host=settings.AUTH_DB_HOST,
        port=settings.AUTH_DB_PORT,
        user=settings.AUTH_DB_USER,
        password=settings.AUTH_DB_PASSWORD,
        database="postgres"
    )
    
    try:
        # Check and create test_financial_auth_db
        result = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = 'test_financial_auth_db'"
        )
        if not result:
            print("Creating test_financial_auth_db...")
            await conn.execute("CREATE DATABASE test_financial_auth_db")
        else:
            print("test_financial_auth_db already exists")
        
        # Check and create test_financial_data_db
        result = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = 'test_financial_data_db'"
        )
        if not result:
            print("Creating test_financial_data_db...")
            await conn.execute("CREATE DATABASE test_financial_data_db")
        else:
            print("test_financial_data_db already exists")
            
    finally:
        await conn.close()
    
    print("Test databases setup completed!")

if __name__ == "__main__":
    asyncio.run(setup_test_databases())

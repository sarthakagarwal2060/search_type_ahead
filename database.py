import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://typeahead_user:typeahead_password@localhost:5432/typeahead_db")

# Global connection pool
pool = None

import asyncio

async def init_db():
    global pool
    for attempt in range(15):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            async with pool.acquire() as conn:
                # Create table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS queries (
                        query TEXT PRIMARY KEY,
                        count BIGINT DEFAULT 1,
                        last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Create a specialized index for fast prefix lookups in Postgres
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_query ON queries (query text_pattern_ops);
                """)
            print("Database initialized successfully.")
            return
        except Exception as e:
            print(f"Database initialization error (Attempt {attempt+1}): {e}. Retrying in 2s...")
            await asyncio.sleep(2)

def get_pool():
    return pool

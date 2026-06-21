import aiosqlite
import logging

DB_FILE = "typeahead.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE NOT NULL,
                count INTEGER DEFAULT 1,
                last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Index on query for fast prefix searching
        await db.execute("CREATE INDEX IF NOT EXISTS idx_query ON queries (query)")
        # Index on count for sorting
        await db.execute("CREATE INDEX IF NOT EXISTS idx_count ON queries (count DESC)")
        await db.commit()
        logging.info("Database initialized successfully.")

async def get_db():
    db = await aiosqlite.connect(DB_FILE)
    # Return dictionary-like rows
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

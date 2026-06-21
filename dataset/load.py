import psycopg2
import csv
import os
import time

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://typeahead_user:typeahead_password@localhost:5432/typeahead_db")

def load_data():
    print("Connecting to Postgres database for initial load...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Create table if not exists (in case the load script runs before init_db)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            query TEXT PRIMARY KEY,
            count BIGINT DEFAULT 1,
            last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    print("Reading CSV and inserting records into Postgres (this may take a moment)...")
    start_time = time.time()
    
    # Fast bulk load using psycopg2 executemany
    # Wait, COPY FROM STDIN is even faster for Postgres
    try:
        with open('dataset/queries.csv', 'r') as f:
            next(f) # Skip header
            cursor.copy_expert("COPY queries (query, count) FROM STDIN WITH CSV", f)
        conn.commit()
    except Exception as e:
        print(f"Bulk load failed (maybe data exists?), error: {e}")
        conn.rollback()
        # Fallback to INSERT ON CONFLICT
        with open('dataset/queries.csv', 'r') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append((row['query'], int(row['count'])))
                if len(batch) >= 10000:
                    psycopg2.extras.execute_values(
                        cursor,
                        "INSERT INTO queries (query, count) VALUES %s ON CONFLICT (query) DO UPDATE SET count = queries.count + EXCLUDED.count",
                        batch
                    )
                    conn.commit()
                    batch = []
            if batch:
                psycopg2.extras.execute_values(
                    cursor,
                    "INSERT INTO queries (query, count) VALUES %s ON CONFLICT (query) DO UPDATE SET count = queries.count + EXCLUDED.count",
                    batch
                )
                conn.commit()

    print("Creating text_pattern_ops index for ultra-fast prefix search...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_query ON queries (query text_pattern_ops);")
    conn.commit()
    
    conn.close()
    print(f"Dataset loaded successfully in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    # We must ensure psycopg2.extras is imported if needed for fallback
    import psycopg2.extras
    load_data()

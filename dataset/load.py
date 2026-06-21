import sqlite3
import csv
import os

DB_FILE = 'typeahead.db'
CSV_FILE = 'dataset/queries.csv'

def load_dataset():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found. Please run generate.py first.")
        return

    print("Connecting to database...")
    # Using sync sqlite3 for bulk loading, since this is a one-time setup script
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Initialize schema just in case
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE NOT NULL,
            count INTEGER DEFAULT 1,
            last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Fast bulk insert settings
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")
    
    print("Reading CSV and inserting records...")
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        batch_size = 10000
        total_inserted = 0
        
        for row in reader:
            query = row['query'].strip().lower()
            count = int(row['count'])
            batch.append((query, count))
            
            if len(batch) >= batch_size:
                cursor.executemany(
                    "INSERT OR IGNORE INTO queries (query, count) VALUES (?, ?)", 
                    batch
                )
                conn.commit()
                total_inserted += len(batch)
                print(f"Inserted {total_inserted} records...")
                batch.clear()
                
        # Insert remaining
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO queries (query, count) VALUES (?, ?)", 
                batch
            )
            conn.commit()
            total_inserted += len(batch)
            print(f"Inserted {total_inserted} records...")
            
    # Create indexes after insertion for speed
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_query ON queries (query)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_count ON queries (count DESC)")
    
    conn.commit()
    conn.close()
    print("Dataset loaded successfully.")

if __name__ == "__main__":
    load_dataset()

import sqlite3
import requests

DB_FILE = "typeahead.db"

def demonstrate_recency_ranking():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create a unique prefix for our test
    prefix = "recencydemo"
    
    # 1. Insert Query A: High count (100), but searched 30 days ago
    c.execute(
        "INSERT OR REPLACE INTO queries (query, count, last_searched_at) VALUES (?, ?, datetime('now', '-30 days'))", 
        (f"{prefix} old_but_popular", 100)
    )
    
    # 2. Insert Query B: Lower count (60), but searched right now
    c.execute(
        "INSERT OR REPLACE INTO queries (query, count, last_searched_at) VALUES (?, ?, datetime('now'))", 
        (f"{prefix} new_and_fresh", 60)
    )
    
    conn.commit()
    conn.close()
    
    print("=== DATABASE STATE ===")
    print("1. 'recencydemo old_but_popular' | Count: 100 | Age: 30 days old")
    print("2. 'recencydemo new_and_fresh'   | Count: 60  | Age: 0 days old (Brand new!)")
    print("\nIf we only used basic sorting (60% marks), 'old_but_popular' would win because 100 > 60.")
    print("\nLet's see what our API returns with Recency-Aware Ranking (Advanced 20% marks):")
    print("-" * 60)
    
    # Call the API bypassing the UI
    try:
        response = requests.get(f"http://localhost:8000/suggest?q={prefix}")
        results = response.json()
        
        for rank, res in enumerate(results, 1):
            print(f"Rank {rank}: '{res['query']}'")
            print(f"         Raw Count: {res['count']}")
            print(f"         Recency-Adjusted Score: {res.get('score', 'N/A'):.2f}\n")
            
    except Exception as e:
        print("Error connecting to API. Make sure uvicorn is running!", e)

if __name__ == "__main__":
    import sys
    try:
        import requests
    except ImportError:
        print("Installing requests library for the test script...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
        
    demonstrate_recency_ranking()

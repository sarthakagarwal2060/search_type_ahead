import asyncio
import asyncpg
import urllib.request
import json
import time

async def test_threshold_rule():
    query_str = "xyz123abc"
    
    # 1. Manually insert with count 999
    conn = await asyncpg.connect("postgresql://typeahead_user:typeahead_password@localhost:5432/typeahead_db")
    await conn.execute("""
        INSERT INTO queries (query, count, last_searched_at) 
        VALUES ($1, $2, CURRENT_TIMESTAMP)
        ON CONFLICT (query) DO UPDATE SET count = $2
    """, query_str, 999)
    await conn.close()
    print(f"Inserted '{query_str}' with count 999 into Postgres.")

    # 2. Send 1 POST /search request
    print("Sending POST /search request...")
    req = urllib.request.Request("http://localhost/search", data=json.dumps({"query": query_str}).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        print("POST response:", response.read().decode('utf-8'))
        
    # 3. Wait for batch writer to flush (interval is 5.0s, we wait 7s to be safe)
    print("Waiting 7 seconds for batch writer to flush and background task to run...")
    await asyncio.sleep(7)
    
    # 4. Check if cache was proactively populated
    print("Checking if cache was proactively populated via GET /suggest...")
    req_get = urllib.request.Request(f"http://localhost/suggest?q={query_str}")
    with urllib.request.urlopen(req_get) as response:
        data = json.loads(response.read().decode('utf-8'))
        print("GET response meta:", data["meta"])
        if data["meta"]["cache_hit"]:
            print("SUCCESS! Cache was proactively populated by the threshold rule.")
        else:
            print("FAILED! Cache miss. The threshold rule did not populate the cache.")

if __name__ == "__main__":
    asyncio.run(test_threshold_rule())

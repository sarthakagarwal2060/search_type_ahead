# Search Typeahead System

A highly optimized, low-latency search typeahead (autocomplete) system designed to handle large datasets, provide recency-aware trending suggestions, and utilize distributed caching and batch writing techniques.

## Features & Architecture

This system was built to satisfy all core and advanced requirements:

1. **FastAPI Backend**: Provides asynchronous, non-blocking HTTP endpoints.
2. **Distributed Cache (Consistent Hashing) with Redis**: A logical `CacheNode` cluster managed by a `ConsistentHashRing`. This assigns prefix queries to specific cache nodes deterministically, guaranteeing high cache-hit rates. Each cache node connects to a distinct Redis Database (`db=0`, `db=1`, etc.) to simulate physically distributed Redis instances. Cache entries have a standard Time-To-Live (TTL).
3. **Recency-Aware Trending Searches**: Implements a time-decay scoring algorithm. Queries are sorted not just by historical popularity, but also by how recently they were searched, giving newer trends a multiplier boost.
4. **Asynchronous Batch Writes**: To protect the database from write-heavy loads, searches are pushed to an in-memory queue. A background worker periodically flushes the queue, aggregating duplicate queries and writing to the database using an atomic `UPSERT`.
5. **SQLite B-Tree Indexing**: The database is structured with a high-performance string index (`CREATE INDEX idx_query ON queries (query)`), allowing incredibly fast prefix lookups (`LIKE 'prefix%'`).
6. **Vanilla JS Debounced UI**: The frontend uses a 300ms debounce technique to prevent rapid-fire API calls while typing, and features keyboard navigation.

## Quickstart (1-Click Docker Setup)

The absolute easiest way to run the entire architecture (FastAPI, dataset generation, SQLite creation, and Redis caching) is using Docker Compose.

Make sure you have Docker installed, then run:

```bash
docker-compose up --build
```

**What this does behind the scenes:**
1. Pulls the official Redis image.
2. Builds the API container.
3. Automatically generates a highly realistic Zipfian dataset of 100,000+ technical/e-commerce queries.
4. Automatically loads it into SQLite and builds the B-Tree indexes.
5. Boots the FastAPI server on port 8000.

Once the logs say "Application startup complete", open your browser to `http://localhost:8000`!

## API Documentation

### `GET /suggest?q=<prefix>`
Returns up to 10 prefix-matching suggestions.
- **q** (string): The search prefix. If empty, returns global trending searches.
- **Returns**: Array of objects `[{"query": "iphone", "count": 1000, "score": 1024.5}]`
- **Behavior**: Checks the Consistent Hashing cache layer. On a cache miss, queries SQLite and applies the recency-aware ranking algorithm.

### `POST /search`
Records a search query.
- **Body**: `{"query": "user search string"}`
- **Returns**: `{"message": "Searched"}`
- **Behavior**: Pushes the query to the in-memory batch writer queue (does not block or write to DB immediately).

### `GET /cache/debug?prefix=<prefix>`
Displays cache routing data.
- **prefix** (string): The prefix to hash.
- **Returns**: `{"prefix": "ip", "assigned_node": "node-2", "cache_hit": true}`

## Design Trade-offs & Explanations

1. **SQLite vs Postgres**: SQLite was chosen for the primary database for ease of local setup and testing. In a true distributed production environment, SQLite would be replaced by a distributed NoSQL store (like Cassandra) or Postgres. The caching layer uses true distributed Redis instances mapped via Consistent Hashing. 
2. **Batch Writing Trade-off**: We batch writes every 5 seconds. The trade-off is data volatility: if the server crashes abruptly, up to 5 seconds of search history is lost. This is an acceptable trade-off for a massive reduction in database I/O, as search count analytics do not strictly require ACID transactions on every keystroke.
3. **Time-Decay Ranking**: The recency formula uses `score = count * (1 + 1 / (max(0, age_hours) + 1))`. This ensures historically massive queries aren't completely wiped out by a single new query, but gives recent trends enough of a boost to surface naturally.

## Testing Recency Ranking (Manual Setup)
To run the math-proof test script, you must be outside Docker. Activate a python environment, run `pip install -r requirements.txt`, and run:
```bash
python3 test_recency.py
```

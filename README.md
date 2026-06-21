# Distributed Search Typeahead System

A highly optimized, low-latency distributed search typeahead (autocomplete) system designed to handle large datasets, provide recency-aware trending suggestions, and utilize advanced distributed caching and batch writing techniques.

## Features & Architecture

This system has been upgraded to a production-grade architecture handling real-world data at scale:

1. **AOL 2006 Real World Dataset**: Downloads and ingests millions of real search logs from the leaked AOL 2006 Search Dataset. The data is parsed dynamically, with chunk caching via Docker volumes to avoid redundant downloads.
2. **PostgreSQL Data Tier**: Replaced SQLite with a robust PostgreSQL 15 database. Configured with optimal Write-Ahead Log (`max_wal_size`) settings to gracefully handle the massive `COPY FROM` bulk-inserts of millions of rows during initialization.
3. **Distributed Nginx Load Balancing**: The system runs two replica FastAPI backends (`api_1` and `api_2`) load-balanced uniformly by an Nginx reverse proxy serving traffic on port `80`.
4. **Distributed Cache (Consistent Hashing) with Redis**: A 3-node Redis cluster (`redis_1`, `redis_2`, `redis_3`) managed by a custom `ConsistentHashRing`. This assigns prefix queries to specific cache nodes deterministically, guaranteeing high cache-hit rates and horizontal scalability.
5. **Proactive Threshold Caching**: A highly efficient batch-writing queue aggregates queries in memory and flushes them to Postgres every 5 seconds. If a query's popularity crosses a specific mathematical threshold (e.g., a multiple of 1,000), it spawns a background worker that proactively fetches, ranks, and pre-warms the Redis cache for all of that query's prefixes. This ensures viral trends are cached *before* the next user searches for them.
6. **Recency-Aware Trending Searches**: Implements a time-decay scoring algorithm. Queries are sorted not just by historical popularity, but also by how recently they were searched, giving newer trends a multiplier boost.
7. **Premium Glassmorphism UI**: A highly responsive vanilla JS frontend featuring debouncing, keyboard navigation, and a live Cache Routing debugging tool.

## Quickstart (Docker Setup)

The absolute easiest way to run the entire distributed architecture is using Docker Compose.

Make sure you have Docker installed, then run:

```bash
docker-compose up --build
```

**What this does behind the scenes:**
1. Spins up PostgreSQL, Nginx, and a 3-node Redis cluster.
2. The primary API container (`api_1`) automatically downloads, decompresses, and counts millions of real search queries from the AOL dataset chunks.
3. It performs a high-speed bulk `COPY` of the generated `queries.csv` into Postgres and builds the indexes. (The CSV is cached on your host via a volume to make future boots instant).
4. Boots the load-balanced FastAPI servers behind Nginx.

Once the logs indicate the system is ready, open your browser to **`http://localhost`** (Port 80)!

## API Documentation

### `GET /suggest?q=<prefix>`
Returns up to 10 prefix-matching suggestions.
- **q** (string): The search prefix. If empty, returns global trending searches.
- **Returns**: Array of objects `[{"query": "google", "count": 1000, "score": 1024.5}]`
- **Behavior**: Checks the Consistent Hashing cache layer. On a cache miss, queries Postgres and applies the recency-aware ranking algorithm. Also returns debug metadata on which node served the request.

### `POST /search`
Records a search query.
- **Body**: `{"query": "user search string"}`
- **Returns**: `{"message": "Searched"}`
- **Behavior**: Pushes the query to the in-memory batch writer queue (does not block or write to DB immediately). Threshold logic may proactively trigger cache population.

## Design Trade-offs & Explanations

1. **Threshold Trigger Math**: To evaluate whether a query crosses the 1000-count threshold during a batch update, we use `(new_count // 1000) > (old_count // 1000)`. This guarantees the cache refresh fires exactly once per threshold boundary crossed, regardless of the size of the batch.
2. **Batch Writing Volatility**: We batch writes every 5 seconds. The trade-off is data volatility: if the server crashes abruptly, up to 5 seconds of search history is lost. This is acceptable for a massive reduction in database I/O, as search analytics do not strictly require ACID transactions on every keystroke.
3. **Time-Decay Ranking**: The recency formula uses `score = count * (1 + 1 / (max(0, age_hours) + 1))`. This ensures historically massive queries aren't completely wiped out by a single new query, but gives recent trends enough of a boost to surface naturally.

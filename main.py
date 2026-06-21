from fastapi import FastAPI, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
import uvicorn
import time
from datetime import datetime
import aiosqlite

from database import init_db, get_db, DB_FILE
from cache import hash_ring
from batch_writer import batch_writer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await batch_writer.start()
    yield
    # Shutdown
    await batch_writer.stop()

app = FastAPI(lifespan=lifespan)

# Allow CORS for easy local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def compute_score(count: int, last_searched_at: str) -> float:
    # Basic recency-aware scoring formula
    # last_searched_at format: 'YYYY-MM-DD HH:MM:SS'
    try:
        dt = datetime.strptime(last_searched_at, "%Y-%m-%d %H:%M:%S")
        age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
        # Give a small boost for recent searches. 
        # Score = count * (1 + 1 / (age_hours + 1))
        # This keeps high-count historically popular queries high, 
        # but gives recent ones an edge if counts are similar.
        # It's a simple decaying multiplier.
        score = count * (1 + 1 / (max(0, age_hours) + 1))
        return score
    except Exception:
        return float(count)

@app.get("/suggest")
async def suggest(q: Optional[str] = Query("")):
    prefix = q.lower().strip()
    
    if not prefix:
        # If no prefix, return overall trending
        # We don't cache global trending for simplicity, but we could.
        async with aiosqlite.connect(DB_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT query, count FROM queries ORDER BY count DESC LIMIT 10")
            rows = await cursor.fetchall()
            return [{"query": row["query"], "count": row["count"]} for row in rows]
            
    node = hash_ring.get_node(prefix)
    cached_results = node.get(prefix)
    
    if cached_results is not None:
        return cached_results
        
    # Cache Miss -> Query Database
    # Fetch top 50 by count to re-rank in memory
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT query, count, last_searched_at FROM queries WHERE query LIKE ? ORDER BY count DESC LIMIT 50",
            (f"{prefix}%",)
        )
        rows = await cursor.fetchall()
        
    # Re-rank with recency
    scored_results = []
    for row in rows:
        score = compute_score(row["count"], row["last_searched_at"])
        scored_results.append({
            "query": row["query"],
            "count": row["count"],
            "score": score
        })
        
    # Sort by score descending
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Take top 10
    top_10 = scored_results[:10]
    
    # Cache the result
    node.set(prefix, top_10, ttl_seconds=60)
    
    return top_10

@app.post("/search")
async def search(payload: dict = Body(...)):
    query = payload.get("query", "").strip().lower()
    if query:
        await batch_writer.add_query(query)
    return {"message": "Searched"}

@app.get("/cache/debug")
async def cache_debug(prefix: str = Query(...)):
    prefix = prefix.lower().strip()
    node = hash_ring.get_node(prefix)
    if not node:
        return {"error": "No cache nodes available"}
        
    cached = node.get(prefix)
    return {
        "prefix": prefix,
        "assigned_node": node.name,
        "cache_hit": cached is not None,
        "ttl_status": "active" if cached is not None else "expired/missing"
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

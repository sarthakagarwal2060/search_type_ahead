from fastapi import FastAPI, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
import uvicorn
import time
from datetime import datetime
from database import init_db, get_pool
from cache import hash_ring, nodes
from batch_writer import batch_writer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await batch_writer.start()
    yield
    # Shutdown
    await batch_writer.stop()
    for node in nodes:
        await node.close()

app = FastAPI(lifespan=lifespan)

# Allow CORS for easy local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def compute_score(count: int, last_searched_at) -> float:
    # Basic recency-aware scoring formula
    try:
        if isinstance(last_searched_at, str):
            # Fallback if passed as string
            dt = datetime.strptime(last_searched_at, "%Y-%m-%d %H:%M:%S")
        else:
            dt = last_searched_at
            
        age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
        # Give a small boost for recent searches. 
        # Score = count * (1 + 1 / (age_hours + 1))
        score = count * (1 + 1 / (max(0, age_hours) + 1))
        return score
    except Exception:
        return float(count)

@app.get("/suggest")
async def suggest(q: Optional[str] = Query("")):
    prefix = q.lower().strip()
    
    meta = {
        "prefix": prefix,
        "assigned_node": "none",
        "cache_hit": False,
        "ttl_status": "expired/missing"
    }
    
    if not prefix:
        # If no prefix, return overall trending
        pool = get_pool()
        if pool:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT query, count FROM queries ORDER BY count DESC LIMIT 10")
                results = [{"query": row["query"], "count": row["count"]} for row in rows]
                return {"results": results, "meta": meta}
        return {"results": [], "meta": meta}
            
    node = hash_ring.get_node(prefix)
    meta["assigned_node"] = node.name
    
    cached_results = await node.get(prefix)
    
    if cached_results is not None:
        meta["cache_hit"] = True
        meta["ttl_status"] = "active"
        return {"results": cached_results, "meta": meta}
        
    # Cache Miss -> Query Database
    # Fetch top 50 by count to re-rank in memory
    pool = get_pool()
    if pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT query, count, last_searched_at FROM queries WHERE query LIKE $1 ORDER BY count DESC LIMIT 50",
                f"{prefix}%"
            )
    else:
        rows = []
        
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
    await node.set(prefix, top_10, ttl_seconds=60)
    
    return {"results": top_10, "meta": meta}

@app.post("/search")
async def search(payload: dict = Body(...)):
    query = payload.get("query", "").strip().lower()
    if query:
        await batch_writer.add_query(query)
    return {"message": "Searched"}



app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

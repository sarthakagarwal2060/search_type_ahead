import asyncio
import logging
from collections import defaultdict
from database import get_pool
from cache import hash_ring

class BatchWriter:
    def __init__(self, flush_interval: float = 5.0, batch_size: int = 100, threshold: int = 1000):
        self.queue = asyncio.Queue()
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.threshold = threshold
        self._task = None
        self._is_running = False

    async def start(self):
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._worker())
            logging.info("Batch writer started.")

    async def stop(self):
        if self._is_running:
            self._is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            await self._flush_queue()
            logging.info("Batch writer stopped.")

    async def add_query(self, query: str):
        await self.queue.put(query)

    async def _worker(self):
        while self._is_running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in batch writer worker: {e}")

    async def _flush_queue(self):
        if self.queue.empty():
            return

        batch_counts = defaultdict(int)
        items_processed = 0
        
        while not self.queue.empty() and items_processed < self.batch_size:
            try:
                query = self.queue.get_nowait()
                batch_counts[query] += 1
                items_processed += 1
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        if not batch_counts:
            return

        pool = get_pool()
        if not pool:
            logging.warning("Database pool not initialized.")
            return

        query_sql = """
            INSERT INTO queries (query, count, last_searched_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT(query) DO UPDATE SET 
                count = queries.count + EXCLUDED.count,
                last_searched_at = CURRENT_TIMESTAMP
            RETURNING count
        """

        try:
            async with pool.acquire() as conn:
                for query, count_increment in batch_counts.items():
                    # Execute individually to get the RETURNING count
                    new_count = await conn.fetchval(query_sql, query, count_increment)
                    
                    # Threshold Logic: Check if we crossed a threshold multiple (e.g., 1000)
                    old_count = new_count - count_increment
                    if (new_count // self.threshold) > (old_count // self.threshold):
                        # Trigger background cache refresh
                        asyncio.create_task(self._refresh_cache_for_query(query))
                        
            logging.info(f"Flushed {items_processed} queries ({len(batch_counts)} unique) to Postgres.")
        except Exception as e:
            logging.error(f"Failed to flush to DB: {e}")

    async def _refresh_cache_for_query(self, query: str):
        from main import compute_score
        pool = get_pool()
        if not pool: return
        
        # We only cache up to 10 characters for prefixes to avoid extreme fanout
        prefixes = [query[:i] for i in range(1, min(len(query)+1, 15))]
        
        try:
            async with pool.acquire() as conn:
                for prefix in prefixes:
                    rows = await conn.fetch(
                        "SELECT query, count, last_searched_at FROM queries WHERE query LIKE $1 ORDER BY count DESC LIMIT 50",
                        f"{prefix}%"
                    )
                    scored = []
                    for r in rows:
                        dt_str = r['last_searched_at'].strftime("%Y-%m-%d %H:%M:%S") if r['last_searched_at'] else None
                        score = compute_score(r['count'], dt_str)
                        scored.append({"query": r['query'], "count": r['count'], "score": score})
                    
                    scored.sort(key=lambda x: x["score"], reverse=True)
                    top_10 = scored[:10]
                    
                    node = hash_ring.get_node(prefix)
                    if node:
                        await node.set(prefix, top_10, ttl_seconds=60)
            logging.info(f"Threshold Refresh: Updated Redis cache for '{query}' prefixes.")
        except Exception as e:
            logging.error(f"Failed to refresh cache for {query}: {e}")

batch_writer = BatchWriter()

import asyncio
import logging
from collections import defaultdict
from database import DB_FILE
import aiosqlite

class BatchWriter:
    def __init__(self, flush_interval: float = 5.0, batch_size: int = 100):
        self.queue = asyncio.Queue()
        self.flush_interval = flush_interval
        self.batch_size = batch_size
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
            # Perform final flush
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

        # Prepare parameters for batch insert
        # SQLite UPSERT: ON CONFLICT(query) DO UPDATE SET count = count + excluded.count, last_searched_at = CURRENT_TIMESTAMP
        values = [(query, count) for query, count in batch_counts.items()]
        
        query_sql = """
            INSERT INTO queries (query, count, last_searched_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(query) DO UPDATE SET 
                count = count + excluded.count,
                last_searched_at = CURRENT_TIMESTAMP
        """

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.executemany(query_sql, values)
                await db.commit()
            logging.info(f"Flushed {items_processed} queries ({len(batch_counts)} unique) to db.")
        except Exception as e:
            logging.error(f"Failed to flush to DB: {e}")

batch_writer = BatchWriter()

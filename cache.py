import hashlib
import json
import os
from typing import Dict, Any, Tuple, List
import bisect
import redis.asyncio as redis

class CacheNode:
    def __init__(self, name: str, host: str):
        self.name = name
        # Connect to a specific Redis container
        self.redis = redis.Redis(host=host, port=6379, db=0, decode_responses=True)

    async def get(self, key: str) -> Any:
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis get error on {self.name}: {e}")
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 60):
        try:
            # Store as JSON string with an expiration TTL
            await self.redis.setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            print(f"Redis set error on {self.name}: {e}")
        
    async def clear(self):
        try:
            await self.redis.flushdb()
        except:
            pass

    async def close(self):
        await self.redis.close()

class ConsistentHashRing:
    def __init__(self, nodes: List[CacheNode], vnodes: int = 100):
        self.vnodes = vnodes
        self.ring: Dict[int, CacheNode] = {}
        self.sorted_keys: List[int] = []
        for node in nodes:
            self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)

    def add_node(self, node: CacheNode):
        for i in range(self.vnodes):
            vnode_key = f"{node.name}-vnode-{i}"
            h = self._hash(vnode_key)
            self.ring[h] = node
            bisect.insort(self.sorted_keys, h)

    def get_node(self, key: str) -> CacheNode:
        if not self.ring:
            return None
        h = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, h)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

# Initialize nodes from environment variable (comma separated)
redis_nodes_env = os.getenv("REDIS_NODES", "localhost")
node_hosts = redis_nodes_env.split(",")

nodes = []
for host in node_hosts:
    nodes.append(CacheNode(host, host))

hash_ring = ConsistentHashRing(nodes)

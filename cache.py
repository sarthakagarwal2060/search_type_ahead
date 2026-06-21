import hashlib
import time
from typing import Dict, Any, Tuple, List
import bisect

class CacheNode:
    def __init__(self, name: str):
        self.name = name
        # store: dict[prefix] = (expiry_timestamp, data)
        self.store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        if key in self.store:
            expiry, data = self.store[key]
            if time.time() < expiry:
                return data
            else:
                # Expired
                del self.store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: float = 60):
        expiry = time.time() + ttl_seconds
        self.store[key] = (expiry, value)
        
    def clear(self):
        self.store.clear()

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

# Initialize nodes
nodes = [CacheNode("node-1"), CacheNode("node-2"), CacheNode("node-3")]
hash_ring = ConsistentHashRing(nodes)

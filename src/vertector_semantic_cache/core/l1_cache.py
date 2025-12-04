from typing import Optional, Dict, Any, Union
from cachetools import LRUCache, LFUCache, TTLCache
import threading
from dataclasses import dataclass
from datetime import datetime
from vertector_semantic_cache.utils.logging import get_logger

logger = get_logger("core.l1_cache")

@dataclass
class L1CacheEntry:
    """Entry stored in L1 cache."""
    response: str
    metadata: Optional[Dict[str, Any]]
    cached_at: datetime
    access_count: int = 0

class L1Cache:
    """In-memory L1 cache with configurable eviction."""
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 300,
        strategy: str = "lru"  # lru, lfu, ttl
    ):
        self._lock = threading.RLock()
        self.strategy = strategy
        
        if strategy == "lru":
            self._cache: Union[LRUCache, LFUCache, TTLCache] = LRUCache(maxsize=max_size)
        elif strategy == "lfu":
            self._cache = LFUCache(maxsize=max_size)
        elif strategy == "ttl":
            self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
            
        logger.info(f"Initialized L1 Cache (strategy={strategy}, max_size={max_size}, ttl={ttl_seconds}s)")
    
    def get(self, key: str) -> Optional[L1CacheEntry]:
        """Get from L1 cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                entry.access_count += 1
                logger.debug(f"L1 HIT for key: {key}")
            else:
                logger.debug(f"L1 MISS for key: {key}")
            return entry
    
    def set(self, key: str, entry: L1CacheEntry) -> None:
        """Set in L1 cache."""
        with self._lock:
            self._cache[key] = entry
            logger.debug(f"L1 SET key: {key}")
    
    def invalidate(self, key: str) -> None:
        """Remove from L1 cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            
    def __len__(self) -> int:
        """Get current size."""
        with self._lock:
            return len(self._cache)

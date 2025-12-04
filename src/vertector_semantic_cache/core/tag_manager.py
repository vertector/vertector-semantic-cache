from typing import List, Optional
from vertector_semantic_cache.utils.logging import get_logger

logger = get_logger("core.tag_manager")

class TagManager:
    """Manage tag-based cache invalidation."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def add_tags(self, cache_key: str, tags: List[str]) -> None:
        """Associate tags with a cache key."""
        if not tags:
            return
            
        pipeline = self.redis.pipeline()
        for tag in tags:
            pipeline.sadd(f"tag:{tag}", cache_key)
        await pipeline.execute()
        logger.debug(f"Added tags {tags} to key {cache_key}")
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with this tag."""
        tag_key = f"tag:{tag}"
        cache_keys = await self.redis.smembers(tag_key)
        
        if not cache_keys:
            return 0
            
        # Convert bytes to strings if needed
        cache_keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in cache_keys]
        
        # Delete all cache entries
        # Note: This deletes the main hash key. RedisVL index might need separate cleanup
        # if it stores vectors separately, but usually it's all in the hash.
        # However, RedisVL uses a specific prefix. We assume cache_key is the full key.
        
        pipeline = self.redis.pipeline()
        if cache_keys:
            pipeline.delete(*cache_keys)
        
        # Delete tag mapping
        pipeline.delete(tag_key)
        
        await pipeline.execute()
        logger.info(f"Invalidated {len(cache_keys)} entries for tag '{tag}'")
        return len(cache_keys)
    
    async def invalidate_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> int:
        """Invalidate by multiple tags."""
        if not tags:
            return 0
            
        tag_keys = [f"tag:{tag}" for tag in tags]
        
        if match_all:
            # Intersection: entries with ALL tags
            cache_keys = await self.redis.sinter(tag_keys)
        else:
            # Union: entries with ANY tag
            cache_keys = await self.redis.sunion(tag_keys)
            
        if not cache_keys:
            return 0
            
        cache_keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in cache_keys]
        
        pipeline = self.redis.pipeline()
        if cache_keys:
            pipeline.delete(*cache_keys)
            
        # We should also clean up the tag sets, but that's harder for intersection/union
        # because we don't know which keys belong to which tag without checking.
        # For now, we leave the tag sets as is (lazy cleanup) or we could iterate.
        # A better approach for tag sets cleanup is to do it when invalidating specific tags.
        # But here we are invalidating *entries*.
        # If we delete the entries, the tag sets will point to non-existent keys.
        # This is fine, but eventually we want to clean up tag sets.
        # For simplicity in this iteration, we just delete the entries.
        
        await pipeline.execute()
        logger.info(f"Invalidated {len(cache_keys)} entries for tags {tags}")
        return len(cache_keys)

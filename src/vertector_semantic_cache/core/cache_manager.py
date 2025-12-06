"""Async semantic cache manager with enterprise features."""

import asyncio
import time
import hashlib
import json
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

try:
    from vertector_semantic_cache.observability.tracing import (
        setup_tracing,
        trace_operation,
        add_span_attributes,
    )
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.query.filter import Tag, FilterExpression
from redisvl.utils.rerank import BaseReranker

from vertector_semantic_cache.core.config import CacheConfig
from vertector_semantic_cache.core.metrics import CacheMetrics
from vertector_semantic_cache.core.l1_cache import L1Cache, L1CacheEntry
from vertector_semantic_cache.core.tag_manager import TagManager
from vertector_semantic_cache.vectorizers.factory import VectorizerFactory
from vertector_semantic_cache.rerankers.factory import RerankerFactory
from vertector_semantic_cache.utils.exceptions import (
    CacheConnectionError,
    CacheOperationError,
)
from vertector_semantic_cache.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class AsyncSemanticCacheManager:
    """
    Enterprise-grade async semantic cache manager.
    
    Features:
    - Full async/await support
    - Optional reranking for improved relevance
    - Retry logic with exponential backoff
    - Comprehensive metrics tracking
    - Context manager support
    - Multi-tenancy with user isolation
    
    Example:
        ```python
        from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig
        
        config = CacheConfig(redis_url="redis://localhost:6380")
        
        async with AsyncSemanticCacheManager(config) as cache:
            # Check cache
            result = await cache.check("What is the capital of France?")
            if result:
                print(f"Cached: {result}")
            else:
                # Call LLM and store
                response = "Paris"
                await cache.store("What is the capital of France?", response)
        ```
    """
    
    def __init__(self, config: CacheConfig):
        """
        Initialize async semantic cache manager.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.metrics = CacheMetrics()
        self._cache: Optional[SemanticCache] = None
        self._l1_cache: Optional[L1Cache] = None
        self.tag_manager: Optional[TagManager] = None
        self._reranker: Optional[BaseReranker] = None
        self._initialized = False
        
        # Setup logging
        setup_logging(
            level=config.log_level,
            json_format=config.json_logging
        )
        
        # Initialize tracing if enabled
        if config.observability.enable_tracing and TRACING_AVAILABLE:
            setup_tracing(
                service_name=config.observability.service_name,
                exporter_type=config.observability.tracing_exporter,
                endpoint=config.observability.tracing_endpoint,
            )
        
        logger.info("Initializing AsyncSemanticCacheManager")
    
    async def initialize(self) -> None:
        """
        Initialize cache connection and components.
        
        Raises:
            CacheConnectionError: If initialization fails
        """
        if self._initialized:
            logger.debug("Cache already initialized")
            return
        
        try:
            logger.info("Creating vectorizer")
            vectorizer = VectorizerFactory.create(self.config.vectorizer)
            
            # Add context_hash to filterable_fields if enabled
            filterable_fields = self.config.filterable_fields or []
            if self.config.enable_context_hashing:
                if "context_hash" not in filterable_fields:
                    filterable_fields = list(filterable_fields) + [{"name": "context_hash", "type": "tag"}]
            
            logger.info(f"Connecting to Redis at {self.config.redis_url}")
            self._cache = SemanticCache(
                name=self.config.name,
                redis_url=self.config.redis_url,
                distance_threshold=self.config.distance_threshold,
                ttl=self.config.ttl,
                vectorizer=vectorizer,
                filterable_fields=filterable_fields,
                connection_kwargs=self.config.connection_kwargs,
                overwrite=self.config.overwrite,
            )
            
            # Initialize reranker if enabled
            if self.config.reranker.enabled:
                logger.info("Creating reranker")
                self._reranker = RerankerFactory.create(self.config.reranker)
            
            # Initialize L1 cache if enabled
            if self.config.l1_cache.enabled:
                logger.info(f"Initializing L1 cache ({self.config.l1_cache.eviction_strategy})")
                self._l1_cache = L1Cache(
                    max_size=self.config.l1_cache.max_size,
                    ttl_seconds=self.config.l1_cache.ttl_seconds,
                    strategy=self.config.l1_cache.eviction_strategy
                )
            
            # Initialize TagManager if enabled
            if self.config.enable_tags:
                logger.info("Initializing TagManager")
                # Get the underlying async redis client from SemanticCache
                # We use the protected method _get_async_redis_client() which ensures it's initialized
                redis_client = await self._cache._get_async_redis_client()
                self.tag_manager = TagManager(redis_client)
            
            self._initialized = True
            logger.info("AsyncSemanticCacheManager initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            raise CacheConnectionError(f"Cache initialization failed: {e}") from e
    
    async def _retry_operation(self, operation, *args, **kwargs):
        """
        Execute operation with retry logic and exponential backoff.
        
        Args:
            operation: Async operation to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
            
        Raises:
            CacheOperationError: If all retries fail
        """
        last_error = None
        delay = self.config.retry_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.config.retry_backoff
                else:
                    logger.error(f"Operation failed after {self.config.max_retries +1} attempts")
        
        self.metrics.record_error()
        raise CacheOperationError(f"Operation failed after retries: {last_error}") from last_error
    
    async def check(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        num_results: int = 5,
        return_fields: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Check cache for semantically similar query.
        
        Args:
            prompt: User query/prompt
            user_id: Optional user identifier for multi-tenancy
            context: Optional context dictionary (e.g. conversation_id, user_persona)
            filters: Optional additional filters
            num_results: Number of results to retrieve before reranking
            return_fields: Fields to return from cache
            
        Returns:
            Cached response if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        self.metrics.increment_query()
        
        # Start tracing span
        trace_ctx = trace_operation(
            "cache.check",
            attributes={
                "cache.prompt_length": len(prompt),
                "cache.user_id": user_id or "none",
                "cache.has_context": bool(context),
            }
        ) if TRACING_AVAILABLE else None
        
        try:
            if trace_ctx:
                span = trace_ctx.__enter__()
            else:
                span = None
            
            # 1. Check L1 Cache (In-Memory)
            if self._l1_cache is not None:
                l1_start = time.time()
                l1_key = self._generate_context_key(prompt, user_id, context)
                l1_entry = self._l1_cache.get(l1_key)
                
                if l1_entry:
                    l1_latency = time.time() - l1_start
                    total_latency = time.time() - start_time
                    
                    # Record metrics
                    self.metrics.record_hit(total_latency)
                    self.metrics.record_l1_hit(l1_latency)
                    if context:
                        # Extract context type for metrics
                        context_type = context.get("user_persona") or context.get("conversation_id") or "unknown"
                        self.metrics.record_context_hit(str(context_type))
                    
                    # Add tracing attributes
                    if span:
                        add_span_attributes(
                            cache_hit=True,
                            cache_layer="L1",
                            latency_ms=total_latency * 1000,
                            l1_latency_ms=l1_latency * 1000,
                        )
                    
                    logger.info(f"L1 Cache HIT for prompt: '{prompt[:50]}...' (latency: {total_latency*1000:.2f}ms)")
                    return l1_entry.response
                else:
                    # L1 miss
                    self.metrics.record_l1_miss()
            
            try:
                # Build filter expression
                # Add context filter if context is provided
                if context and self.config.enable_context_hashing:
                    context_str = json.dumps(context, sort_keys=True)
                    context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
                    if filters is None:
                        filters = {}
                    filters["context_hash"] = context_hash
                    
                filter_expression = self._build_filter_expression(user_id, filters)
                
                # Check cache (L2)
                # Check cache (L2)
                l2_start = time.time()
                
                async def _check():
                    # Generate embedding
                    vector = self._cache._vectorizer.embed(prompt)
                    if isinstance(vector, list) and isinstance(vector[0], list):
                        vector = vector[0]
                    
                    # Prepare query parameters
                    import numpy as np
                    vector_blob = np.array(vector, dtype=np.float32).tobytes()
                    threshold = float(self.config.distance_threshold)
                    
                    # Build native RediSearch query
                    # Using VECTOR_RANGE to enforce threshold at DB level
                    # syntax: @prompt_vector:[VECTOR_RANGE {radius} $blob]=>{$YIELD_DISTANCE_AS: vector_distance}
                    
                    base_query = f"@prompt_vector:[VECTOR_RANGE {threshold} $blob]=>{{$YIELD_DISTANCE_AS: vector_distance}}"
                    
                    # Add filters if present
                    if filter_expression:
                        # RedisVL filter expression string conversion is needed
                        # Simplification: if we have filters, we might need to combine them
                        # For now, we'll prefix them: (@filter) @vector:[...]
                        filter_str = str(filter_expression)
                        query_str = f"({filter_str}) {base_query}"
                    else:
                        query_str = base_query

                    # Execute raw command
                    # FT.SEARCH {index_name} {query} PARAMS 2 blob {vector_blob} SORTBY vector_distance ASC LIMIT 0 {num_results} DIALECT 2
                    try:
                        cmd = [
                            "FT.SEARCH",
                            self.config.name,  # Index name usually matches cache name
                            query_str,
                            "PARAMS", "2", "blob", vector_blob,
                            "SORTBY", "vector_distance", "ASC",
                            "LIMIT", "0", str(num_results),
                            # DIALECT 2 is needed for vector search
                            "DIALECT", "2"
                        ]
                        
                        redis_client = await self._cache._get_async_redis_client()
                        raw_results = await redis_client.execute_command(*cmd)
                        
                        # Parse raw results
                        # [count, key1, [field, val, ...], key2, ...]
                        count = raw_results[0]
                        parsed_results = []
                        
                        for i in range(1, len(raw_results), 2):
                            key = raw_results[i]
                            fields_raw = raw_results[i+1]
                            
                            # Convert list [k, v, k, v] to dict
                            doc = {
                                "metadata": {}
                            }
                            
                            for j in range(0, len(fields_raw), 2):
                                # Decode bytes to str
                                f_name = fields_raw[j].decode('utf-8') if isinstance(fields_raw[j], bytes) else fields_raw[j]
                                f_val_raw = fields_raw[j+1]
                                f_val = f_val_raw.decode('utf-8') if isinstance(f_val_raw, bytes) else f_val_raw
                                
                                if f_name == "vector_distance":
                                    doc["vector_distance"] = float(f_val)
                                elif f_name == "prompt":
                                    doc["prompt"] = f_val
                                elif f_name == "response":
                                    doc["response"] = f_val
                                elif f_name == "prompt_vector":
                                    # Skip vector data in output
                                    pass
                                else:
                                    # All other fields go into metadata
                                    # Try to parse JSON if it looks like it?
                                    # RedisVL might store simple types.
                                    doc["metadata"][f_name] = f_val
                            
                            parsed_results.append(doc)
                            
                        return parsed_results
                        
                    except Exception as e:
                        logger.error(f"Native vector search failed: {e}")
                        # Fallback to redisvl if native fails (though unlikely)
                        return await self._cache.acheck(
                            prompt=prompt,
                            num_results=num_results,
                            return_fields=return_fields or ["response", "prompt", "metadata"],
                            filter_expression=filter_expression,
                        )
                
                cached_results = await self._retry_operation(_check)
                
                if cached_results and len(cached_results) > 0:
                    # Double check distance (sanity check)
                    result = cached_results[0]
                    if "vector_distance" in result:
                        distance = float(result["vector_distance"])
                        if distance > self.config.distance_threshold:
                            # This should happen rarely with VECTOR_RANGE, but precision errors exist
                            logger.info(f"L2 Cache MISS (Post-filter): {distance:.4f}")
                            self.metrics.record_miss()
                            return None
                    
                    # Apply reranking if enabled
                    if self._reranker:
                        cached_results = await self._rerank_results(prompt, cached_results)
                        self.metrics.record_rerank()
                    
                    # Record L2 hit
                    l2_latency = time.time() - l2_start
                    total_latency = time.time() - start_time
                    self.metrics.record_hit(total_latency)
                    self.metrics.record_l2_hit(l2_latency)
                    
                    if context:
                        context_type = context.get("user_persona") or context.get("conversation_id") or "unknown"
                        self.metrics.record_context_hit(str(context_type))
                    
                    # Add tracing attributes
                    if span:
                        add_span_attributes(
                            cache_hit=True,
                            cache_layer="L2",
                            latency_ms=total_latency * 1000,
                            l2_latency_ms=l2_latency * 1000,
                        )
                    
                    logger.info(
                        f"Cache HIT for prompt: '{prompt[:50]}...' "
                        f"(threshold: {self.config.distance_threshold}, "
                        f"latency: {total_latency*1000:.2f}ms)"
                    )
                    
                    # Check staleness if enabled
                    if self.config.enable_stale_while_revalidate and cached_results:
                        entry_age = self._get_entry_age(cached_results[0])
                        
                        # Check if entry is stale (older than TTL)
                        if entry_age > (self.config.ttl or 3600):
                            if entry_age < self.config.max_stale_age_seconds:
                                # Serve stale + trigger background refresh
                                self.metrics.record_stale_served(entry_age)
                                logger.info(
                                    f"Serving stale entry (age={entry_age:.0f}s), "
                                    f"refreshing in background"
                                )
                                
                                # Trigger background refresh asynchronously
                                # Note: Background refresh requires user to re-call LLM
                                # This is a notification mechanism, not automatic LLM call
                                asyncio.create_task(
                                    self._background_refresh_notification(
                                        prompt=prompt,
                                        user_id=user_id,
                                        context=context,
                                        entry_age=entry_age
                                    )
                                )
                            else:
                                # Too stale, refuse to serve
                                self.metrics.record_stale_refused()
                                logger.warning(
                                    f"Entry too stale (age={entry_age:.0f}s > max={self.config.max_stale_age_seconds}), "
                                    f"refusing to serve"
                                )
                                # Return None to force fresh fetch
                                self.metrics.record_miss()
                                self.metrics.record_l2_miss()
                                return None
                    
                    # Check version if enabled
                    if self.config.enable_version_checking and cached_results:
                        stored_version = cached_results[0].get("metadata", {}).get("cache_version")
                        if stored_version and stored_version != self.config.cache_version:
                            self.metrics.record_version_mismatch()
                            logger.info(
                                f"Version mismatch: stored={stored_version} != "
                                f"current={self.config.cache_version}, invalidating"
                            )
                            # Return None to force fresh fetch
                            self.metrics.record_miss()
                            self.metrics.record_l2_miss()
                            return None
                    
                    response = cached_results[0].get("response")
                    
                    # Update L1 Cache
                    if self._l1_cache is not None and response:
                        from datetime import datetime, timezone
                        l1_key = self._generate_context_key(prompt, user_id, context)
                        self._l1_cache.set(l1_key, L1CacheEntry(
                            response=response,
                            metadata=cached_results[0].get("metadata"),
                            cached_at=datetime.now(timezone.utc)
                        ))
                    
                    return response
                else:
                    # L2 miss
                    self.metrics.record_miss()
                    self.metrics.record_l2_miss()
                    
                    if span:
                        add_span_attributes(
                            cache_hit=False,
                            cache_layer="L2",
                        )
                    
                    logger.info(f"Cache MISS for prompt: '{prompt[:50]}...'")
                    return None
            
            except Exception as e:
                logger.error(f"Error checking cache: {e}")
                self.metrics.record_error()
                if span:
                    add_span_attributes(error=True, error_message=str(e))
                # Graceful degradation - return None on error
                return None
        
        finally:
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)
    
    async def store(
        self,
        prompt: str,
        response: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Store prompt-response pair in cache.
        
        Args:
            prompt: User query/prompt
            response: LLM response to cache
            user_id: Optional user identifier
            context: Optional context dictionary
            metadata: Additional metadata to store
            tags: Optional list of tags for invalidation
            filters: Optional filter tags
            ttl: Optional TTL override for this entry
            
        Returns:
            Redis key for the cached entry
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Prepare metadata
            cache_metadata = metadata or {}
            from datetime import datetime, timezone
            cache_metadata["cached_at"] = datetime.now(timezone.utc).isoformat()
            
            # Prepare filters
            filter_dict = {}
            if user_id:
                filter_dict["user_id"] = user_id
            if filters:
                filter_dict.update(filters)
            
            # Add context to metadata and filters if configured
            if context:
                if self.config.enable_context_hashing:
                    # Add context hash to metadata
                    context_str = json.dumps(context, sort_keys=True)
                    context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
                    cache_metadata["context_hash"] = context_hash
                    
                    # Add to filters for L2 retrieval
                    filter_dict["context_hash"] = context_hash
                
                # Store full context in metadata
                cache_metadata["context"] = context
            
            # Store in cache
            async def _store():
                return await self._cache.astore(
                    prompt=prompt,
                    response=response,
                    metadata=cache_metadata,
                    filters=filter_dict if filter_dict else None,
                    ttl=ttl,
                )
            
            key = await self._retry_operation(_store)
            logger.info(f"Stored in cache: '{prompt[:50]}...' (key: {key})")
            
            # Store in L1 Cache
            if self._l1_cache is not None:
                l1_key = self._generate_context_key(prompt, user_id, context)
                self._l1_cache.set(l1_key, L1CacheEntry(
                    response=response,
                    metadata=cache_metadata,
                    cached_at=datetime.now(timezone.utc)
                ))
            
            # Add tags if enabled
            if tags and self.tag_manager:
                await self.tag_manager.add_tags(key, tags)
            
            return key
        
        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
            self.metrics.record_error()
            raise CacheOperationError(f"Failed to store in cache: {e}") from e
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if self._l1_cache is not None:
                self._l1_cache.clear()
                
            await self._cache.aclear()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise CacheOperationError(f"Failed to clear cache: {e}") from e
    
    async def delete(self) -> None:
        """Delete the cache and its index entirely."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if self._l1_cache is not None:
                self._l1_cache.clear()
                
            await self._cache.adelete()
            logger.info("Cache deleted")
        except Exception as e:
            logger.error(f"Error deleting cache: {e}")
            raise CacheOperationError(f"Failed to delete cache: {e}") from e
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with this tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            Number of invalidated entries
        """
        if not self._initialized:
            await self.initialize()
            
        if not self.tag_manager:
            logger.warning("TagManager not enabled. Cannot invalidate by tag.")
            return 0
            
        # Clear L1 cache to ensure consistency
        if self._l1_cache is not None:
            self._l1_cache.clear()
            
        return await self.tag_manager.invalidate_by_tag(tag)
        
    async def invalidate_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> int:
        """
        Invalidate by multiple tags.
        
        Args:
            tags: List of tags
            match_all: If True, invalidate entries having ALL tags.
                       If False, invalidate entries having ANY tag.
                       
        Returns:
            Number of invalidated entries
        """
        if not self._initialized:
            await self.initialize()
            
        if not self.tag_manager:
            logger.warning("TagManager not enabled. Cannot invalidate by tags.")
            return 0
            
        # Clear L1 cache to ensure consistency
        if self._l1_cache is not None:
            self._l1_cache.clear()
            
        return await self.tag_manager.invalidate_by_tags(tags, match_all)
    
    async def batch_check(
        self,
        prompts: List[str],
        user_ids: Optional[List[str]] = None,
        contexts: Optional[List[Dict[str, Any]]] = None,
        num_results: int = 5,
        return_fields: Optional[List[str]] = None,
    ) -> List[Optional[str]]:
        """
        Check cache for multiple prompts in parallel (5-10x faster).
        
        This is significantly faster than calling check() sequentially because:
        - Parallel L1 cache lookups
        - Concurrent L2 queries with asyncio.gather
        - Reduced overhead
        
        Args:
            prompts: List of prompts to check
            user_ids: Optional list of user IDs (one per prompt, or None)
            contexts: Optional list of contexts (one per prompt, or None)
            num_results: Number of results to retrieve per prompt
            return_fields: Fields to return from cache
            
        Returns:
            List of cached responses (None if not found)
            
        Example:
            >>> prompts = ["What is AI?", "What is ML?", "What is DL?"]
            >>>results = await cache.batch_check(prompts)
            >>> # Returns: [response1, response2, None]  # One cache miss
        """
        if not self._initialized:
            await self.initialize()
        
        if not prompts:
            return []
        
        # Normalize inputs
        n = len(prompts)
        user_ids = user_ids or [None] * n
        contexts = contexts or [None] * n
        
        if len(user_ids) != n or len(contexts) != n:
            raise ValueError("user_ids and contexts lists must match prompts length")
        
        start_time = time.time()
        results: List[Optional[str]] = [None] * n
        l2_indices: List[int] = []  # Indices that need L2 lookup
        
        # Track metrics
        for _ in prompts:
            self.metrics.increment_query()
        
        # Phase 1: Check L1 cache for all prompts
        if self._l1_cache is not None:
            for i, (prompt, user_id, context) in enumerate(zip(prompts, user_ids, contexts)):
                l1_start = time.time()
                l1_key = self._generate_context_key(prompt, user_id, context)
                l1_entry = self._l1_cache.get(l1_key)
                
                if l1_entry:
                    l1_latency = time.time() - l1_start
                    total_latency = time.time() - start_time
                    
                    # Record metrics
                    self.metrics.record_hit(total_latency)
                    self.metrics.record_l1_hit(l1_latency)
                    if context:
                        context_type = context.get("user_persona") or context.get("conversation_id") or "unknown"
                        self.metrics.record_context_hit(str(context_type))
                    
                    results[i] = l1_entry.response
                else:
                    self.metrics.record_l1_miss()
                    l2_indices.append(i)
        else:
            l2_indices = list(range(n))
        
        # Phase 2: Parallel L2 lookup for L1 misses
        if l2_indices:
            l2_start = time.time()
            
            # Create parallel L2 check tasks
            l2_tasks = []
            for idx in l2_indices:
                prompt = prompts[idx]
                user_id = user_ids[idx]
                context = contexts[idx]
                
                # Build filter
                filters = {}
                if context and self.config.enable_context_hashing:
                    context_str = json.dumps(context, sort_keys=True)
                    context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
                    filters["context_hash"] = context_hash
                
                filter_expression = self._build_filter_expression(user_id, filters)
                
                # Define async task
                async def _check_one(p=prompt, fe=filter_expression):
                    try:
                        return await self._cache.acheck(
                            prompt=p,
                            num_results=num_results,
                            return_fields=return_fields or ["response", "prompt", "metadata"],
                            filter_expression=fe,
                        )
                    except Exception as e:
                        logger.error(f"Error in L2 check: {e}")
                        return None
                
                l2_tasks.append(_check_one())
            
            # Execute all L2 checks concurrently
            l2_results_list = await asyncio.gather(*l2_tasks)
            
            l2_latency = time.time() - l2_start
            
            # Process L2 results
            for idx, l2_result in zip(l2_indices, l2_results_list):
                if l2_result and len(l2_result) > 0:
                    # L2 hit
                    total_latency = time.time() - start_time
                    self.metrics.record_hit(total_latency)
                    self.metrics.record_l2_hit(l2_latency / len(l2_indices))
                    
                    if contexts[idx]:
                        context_type = contexts[idx].get("user_persona") or contexts[idx].get("conversation_id") or "unknown"
                        self.metrics.record_context_hit(str(context_type))
                    
                    response = l2_result[0].get("response")
                    results[idx] = response
                    
                    # Populate L1 cache
                    if self._l1_cache is not None and response:
                        from datetime import datetime, timezone
                        l1_key = self._generate_context_key(prompts[idx], user_ids[idx], contexts[idx])
                        self._l1_cache.set(l1_key, L1CacheEntry(
                            response=response,
                            metadata=l2_result[0].get("metadata"),
                            cached_at=datetime.now(timezone.utc)
                        ))
                else:
                    # L2 miss
                    self.metrics.record_miss()
                    self.metrics.record_l2_miss()
        
        logger.info(
            f"Batch check: {len(prompts)} prompts, "
            f"{sum(1 for r in results if r)} hits, "
            f"{sum(1 for r in results if r is None)} misses, "
            f"{(time.time() - start_time)*1000:.2f}ms"
        )
        
        return results


    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if not self._initialized or not self._cache:
            return
        
        try:
            logger.info("Disconnecting from Redis...")
            await self._cache.adisconnect()
            self._initialized = False
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.warning(f"Error during disconnect (non-fatal): {e}")
            self._initialized = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        return self.metrics.to_dict()
    
    def get_metrics_prometheus(self) -> str:
        """Get metrics in Prometheus format."""
        return self.metrics.to_prometheus()
    
    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self.metrics.reset()
        logger.info("Metrics reset")
    
    def set_threshold(self, threshold: float) -> None:
        """
        Adjust semantic similarity threshold.
        
        Args:
            threshold: New threshold value (0.0-1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.config.distance_threshold = threshold
        if self._cache:
            self._cache.set_threshold(threshold)
        logger.info(f"Threshold updated to {threshold}")
    
    def set_ttl(self, ttl: int) -> None:
        """
        Set default TTL for cache entries.
        
        Args:
            ttl: TTL in seconds
        """
        self.config.ttl = ttl
        if self._cache:
            self._cache.set_ttl(ttl)
        logger.info(f"TTL updated to {ttl}s")
        
    async def _background_refresh_notification(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        entry_age: float = 0.0
    ) -> None:
        """Notify about stale entry that needs refresh.
        
        This is a placeholder for background refresh logic. In practice, you would:
        1. Call your LLM to get fresh response
        2. Store the updated response back in cache
        3. Log the refresh operation
        
        For now, this just logs the notification.
        
        Args:
            prompt: The stale prompt
            user_id: Optional user ID
            context: Optional context
            entry_age: Age of the stale entry in seconds
        """
        logger.debug(
            f"Background refresh triggered for prompt: '{prompt[:50]}...' "
            f"(age={entry_age:.0f}s)"
        )
        
        # If user provided a refresh callback, call it
        if self.config.stale_refresh_callback:
            try:
                logger.info(f"Calling user refresh callback for stale entry")
                # Call user's refresh function
                fresh_response = await self.config.stale_refresh_callback(
                    prompt=prompt,
                    user_id=user_id,
                    context=context
                )
                
                # Store the fresh response
                if fresh_response:
                    await self.store(
                        prompt=prompt,
                        response=fresh_response,
                        user_id=user_id,
                        context=context
                    )
                    logger.info(f"Background refresh completed successfully")
            except Exception as e:
                logger.error(f"Error in background refresh callback: {e}")
        else:
            # No callback provided - just log for user awareness
            logger.debug(
                "No refresh callback configured. To enable automatic refresh, "
                "set stale_refresh_callback in CacheConfig"
            )
    
    def _get_entry_age(self, cache_result: Dict[str, Any]) -> float:
        """Calculate age of cache entry in seconds.
        
        Args:
            cache_result: Cache result with metadata
            
        Returns:
            Age in seconds, or 0 if no timestamp found
        """
        try:
            from datetime import datetime, timezone
            stored_at_str = cache_result.get("metadata", {}).get("stored_at")
            if not stored_at_str:
                return 0.0
            
            stored_at = datetime.fromisoformat(stored_at_str.replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - stored_at).total_seconds()
            return age
        except Exception as e:
            logger.warning(f"Error calculating entry age: {e}")
            return 0.0
    
    def _generate_context_key(
        self,
        prompt: str,
        user_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key including context."""
        key_parts = [prompt]
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        if context and self.config.enable_context_hashing:
            # Filter context fields if configured
            ctx_to_hash = context
            if self.config.context_fields:
                ctx_to_hash = {
                    k: v for k, v in context.items() 
                    if k in self.config.context_fields
                }
            
            if ctx_to_hash:
                # Hash context for deterministic key
                context_str = json.dumps(ctx_to_hash, sort_keys=True)
                context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
                key_parts.append(f"ctx:{context_hash}")
        
        return ":".join(key_parts)
    
    def _build_filter_expression(
        self,
        user_id: Optional[str],
        filters: Optional[Dict[str, Any]]
    ) -> Optional[FilterExpression]:
        """Build filter expression for cache queries."""
        if not user_id and not filters:
            return None
        
        filter_parts = []
        if user_id:
            filter_parts.append(Tag("user_id") == user_id)
        if filters:
            for key, value in filters.items():
                filter_parts.append(Tag(key) == value)
        
        if len(filter_parts) == 0:
            return None
        elif len(filter_parts) == 1:
            return filter_parts[0]
        else:
            result = filter_parts[0]
            for fp in filter_parts[1:]:
                result = result & fp
            return result
    
    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank cache results for improved relevance."""
        if not self._reranker or not results:
            return results
        
        try:
            # Prepare documents for reranking
            docs = [{"content": r.get("prompt", "")} for r in results]
            
            # Rerank
            reranked = await self._reranker.arank(query=query, docs=docs)
            
            # Map back to original results
            if isinstance(reranked, tuple):
                reranked_docs, scores = reranked
                reranked_results = []
                for doc, score in zip(reranked_docs, scores):
                    # Find original result
                    for r in results:
                        if r.get("prompt") == doc.get("content"):
                            result_copy = r.copy()
                            result_copy["rerank_score"] = score
                            reranked_results.append(result_copy)
                            break
                return reranked_results
            else:
                return reranked
        
        except Exception as e:
            logger.warning(f"Reranking failed: {e}. Returning original results.")
            return results
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False

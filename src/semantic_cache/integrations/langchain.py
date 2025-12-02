"""Async LangChain integration with semantic caching."""

import time
from typing import Optional, List, Dict, Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from semantic_cache.core.cache_manager import AsyncSemanticCacheManager
from semantic_cache.utils.logging import get_logger

logger = get_logger(__name__)


class AsyncLangChainCachedLLM:
    """
    Async LangChain LLM wrapper with semantic caching.
    
    This class wraps any LangChain chat model and adds semantic caching capabilities.
    It automatically checks the cache before calling the LLM and stores responses
    for future use.
    
    Example:
        ```python
        from langchain_google_genai import ChatGoogleGenerativeAI
        from semantic_cache import AsyncSemanticCacheManager, CacheConfig
        from semantic_cache.integrations import AsyncLangChainCachedLLM
        
        # Setup cache
        cache_config = CacheConfig(redis_url="redis://localhost:6380")
        cache_manager = AsyncSemanticCacheManager(cache_config)
        
        # Setup LLM with caching
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        cached_llm = AsyncLangChainCachedLLM(cache_manager, llm)
        
        # Use it
        async with cache_manager:
            response = await cached_llm.query(
                prompt="What is the capital of France?",
                system_message="You are a helpful assistant."
            )
        ```
    """
    
    def __init__(
        self,
        cache: AsyncSemanticCacheManager,
        llm: BaseChatModel,
    ):
        """
        Initialize async LangChain cached LLM.
        
        Args:
            cache: Async semantic cache manager instance
            llm: LangChain chat model instance
        """
        self.cache = cache
        self.llm = llm
        logger.info(f"Initialized AsyncLangChainCachedLLM with {type(llm).__name__}")
    
    async def query(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        user_id: Optional[str] = None,
        use_cache: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Query LLM with automatic caching.
        
        Args:
            prompt: User query/prompt
            system_message: Optional system message
            user_id: Optional user identifier for multi-tenancy
            use_cache: Whether to use cache (default: True)
            metadata: Optional metadata to store with cached response
            
        Returns:
            LLM response (from cache or fresh)
        """
        # Check cache first
        if use_cache:
            cached_response = await self.cache.check(prompt, user_id=user_id)
            if cached_response:
                logger.info("✓ Cache hit! Returning cached response")
                return cached_response
        
        # Cache miss - call LLM
        logger.info(f"✗ Cache miss. Calling LLM for: '{prompt[:50]}...'")
        start_time = time.time()
        
        try:
            # Prepare messages
            messages: List[BaseMessage] = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))
            
            # Call LLM
            response = await self.llm.ainvoke(messages)
            response_text = response.content
            
            llm_latency = time.time() - start_time
            logger.info(f"LLM responded in {llm_latency:.2f}s")
            
            # Store in cache
            if use_cache:
                cache_metadata = metadata or {}
                cache_metadata["llm_latency"] = llm_latency
                cache_metadata["model"] = getattr(self.llm, "model_name", "unknown")
                
                await self.cache.store(
                    prompt=prompt,
                    response=response_text,
                    user_id=user_id,
                    metadata=cache_metadata,
                )
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
    
    async def stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        user_id: Optional[str] = None,
        use_cache: bool = True,
    ):
        """
        Stream LLM response with caching.
        
        Note: Streaming responses are accumulated and then cached after completion.
        If a cached response exists, it will be yielded in chunks to simulate streaming.
        
        Args:
            prompt: User query/prompt
            system_message: Optional system message
            user_id: Optional user identifier
            use_cache: Whether to use cache
            
        Yields:
            Response chunks
        """
        # Check cache first
        if use_cache:
            cached_response = await self.cache.check(prompt, user_id=user_id)
            if cached_response:
                logger.info("✓ Cache hit! Streaming cached response")
                # Simulate streaming by yielding in chunks
                chunk_size = 10
                for i in range(0, len(cached_response), chunk_size):
                    yield cached_response[i:i+chunk_size]
                return
        
        # Cache miss - stream from LLM
        logger.info(f"✗ Cache miss. Streaming from LLM for: '{prompt[:50]}...'")
        
        # Prepare messages
        messages: List[BaseMessage] = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        # Accumulate response for caching
        full_response = ""
        
        try:
            async for chunk in self.llm.astream(messages):
                chunk_text = chunk.content
                full_response += chunk_text
                yield chunk_text
            
            # Store complete response in cache
            if use_cache and full_response:
                await self.cache.store(
                    prompt=prompt,
                    response=full_response,
                    user_id=user_id,
                )
        
        except Exception as e:
            logger.error(f"Error streaming from LLM: {e}")
            raise

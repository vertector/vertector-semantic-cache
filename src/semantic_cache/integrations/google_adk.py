"""Async Google ADK integration with semantic caching."""

import time
from typing import Optional, Dict, Any

from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.sessions import InMemorySessionService
from google.adk import Runner
from google.genai import types

from semantic_cache.core.cache_manager import AsyncSemanticCacheManager
from semantic_cache.utils.logging import get_logger

logger = get_logger(__name__)


class AsyncGoogleADKCachedAgent:
    """
    Async Google ADK Agent wrapper with semantic caching.
    
    This class wraps a Google ADK Agent and adds semantic caching capabilities.
    It automatically checks the cache before calling the agent and stores responses
    for future use.
    
    Example:
        ```python
        from google.adk.agents import Agent
        from google.adk.apps.app import App
        from semantic_cache import AsyncSemanticCacheManager, CacheConfig
        from semantic_cache.integrations import AsyncGoogleADKCachedAgent
        
        # Setup cache
        cache_config = CacheConfig(redis_url="redis://localhost:6380")
        cache_manager = AsyncSemanticCacheManager(cache_config)
        
        # Setup agent
        agent = Agent(
            name="my_agent",
            model="gemini-2.5-flash",
            instruction="You are a helpful assistant."
        )
        app = App(name="my_app", root_agent=agent)
        
        # Create cached agent
        cached_agent = AsyncGoogleADKCachedAgent(cache_manager, agent, app)
        
        # Use it
        async with cache_manager:
            response = await cached_agent.query(
                prompt="What is the capital of France?",
                user_id="user123"
            )
        ```
    """
    
    def __init__(
        self,
        cache: AsyncSemanticCacheManager,
        agent: Agent,
        app: App,
    ):
        """
        Initialize async Google ADK cached agent.
        
        Args:
            cache: Async semantic cache manager instance
            agent: Google ADK agent instance
            app: Google ADK app instance
        """
        self.cache = cache
        self.agent = agent
        self.app = app
        self.session_service = InMemorySessionService()
        self.runner = Runner(app=app, session_service=self.session_service)
        self.sessions: Dict[str, str] = {}  # user_id -> session_id
        
        logger.info(f"Initialized AsyncGoogleADKCachedAgent with agent: {agent.name}")
    
    async def create_session(self, user_id: str) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Session ID
        """
        session = await self.session_service.create_session(
            app_name=self.app.name,
            user_id=user_id,
            state={}
        )
        self.sessions[user_id] = session.id
        logger.info(f"Created session {session.id} for user {user_id}")
        return session.id
    
    async def query(
        self,
        prompt: str,
        user_id: str = "default_user",
        use_cache: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Query agent with automatic caching.
        
        Args:
            prompt: User query/prompt
            user_id: User identifier
            use_cache: Whether to use cache
            metadata: Optional metadata to store
            
        Returns:
            Agent response (from cache or fresh)
        """
        # Check cache first
        if use_cache:
            cached_response = await self.cache.check(prompt, user_id=user_id)
            if cached_response:
                logger.info("✓ Cache hit! Returning cached response")
                return cached_response
        
        # Cache miss - call agent
        logger.info(f"✗ Cache miss. Calling agent for: '{prompt[:50]}...'")
        start_time = time.time()
        
        try:
            # Ensure session exists
            if user_id not in self.sessions:
                await self.create_session(user_id)
            
            session_id = self.sessions[user_id]
            
            # Call agent asynchronously
            content = types.Content(role='user', parts=[types.Part(text=prompt)])
            
            # The runner's run method is synchronous, so we need to handle it differently
            # For now, we'll use asyncio.to_thread to run it in a thread pool
            import asyncio
            events = await asyncio.to_thread(
                self.runner.run,
                user_id=user_id,
                session_id=session_id,
                new_message=content
            )
            
            # Extract response from events
            response_text = None
            for event in events:
                if event.is_final_response():
                    response_text = event.content.parts[0].text
                    break
            
            if not response_text:
                raise ValueError("No response from agent")
            
            agent_latency = time.time() - start_time
            logger.info(f"Agent responded in {agent_latency:.2f}s")
            
            # Store in cache
            if use_cache:
                cache_metadata = metadata or {}
                cache_metadata["agent_latency"] = agent_latency
                cache_metadata["agent_name"] = self.agent.name
                
                await self.cache.store(
                    prompt=prompt,
                    response=response_text,
                    user_id=user_id,
                    metadata=cache_metadata,
                )
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error calling agent: {e}")
            raise
    
    async def close(self) -> None:
        """Close the runner and clean up resources."""
        try:
            await self.runner.close()
            logger.info("Agent runner closed")
        except Exception as e:
            logger.error(f"Error closing runner: {e}")

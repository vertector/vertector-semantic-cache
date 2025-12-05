"""Google ADK integration example."""

import asyncio
import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.tools import google_search

from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from vertector_semantic_cache.integrations import AsyncGoogleADKCachedAgent

# Load environment variables
load_dotenv()


async def google_adk_example():
    """Demonstrate Google ADK integration with semantic caching."""
    print("\n" + "="*70)
    print("Google ADK Integration Example")
    print("="*70 + "\n")
    
    # Setup cache
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="adk_cache",
        distance_threshold=0.25,
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Define agent directly in this file (avoids Google ADK path inference)
    # Key insight: When agents are defined locally, not imported from packages,
    # Google ADK doesn't infer app names from paths - you can use any name!
    agent = Agent(
        name="crypto_assistant",
        model="gemini-2.5-flash",
        instruction="You are a helpful cryptocurrency assistant. Answer questions about crypto concisely.",
        description="A cached crypto assistant",
        tools=[google_search]
    )
    
    # Now you can use ANY app name you want! No warnings!
    app = App(
        name="my_awesome_crypto_app",  # ✅ ANY name works!
        root_agent=agent
    )
    
    # Create cached agent
    cached_agent = AsyncGoogleADKCachedAgent(cache_manager, agent, app)
    
    # Test queries
    test_queries = [
        "What are the top 3 cryptocurrencies?",
        "Tell me about the best 3 crypto coins",  # Semantically similar
        "What is Bitcoin?",
        "Explain Bitcoin to me",  # Semantically similar
    ]
    
    async with cache_manager:
        for i, query in enumerate(test_queries, 1):
            print(f"\n[Query {i}] {query}")
            response = await cached_agent.query(query, user_id="crypto_user")
            print(f"Response: {response[:150]}...")
            print("-" * 70)
        
        print("\n✅ Google ADK example complete!\n")
        
        # Cleanup
        await cached_agent.close()


async def multi_user_example():
    """Demonstrate multi-user cache isolation."""
    print("\n" + "="*70)
    print("Multi-User Cache Isolation Example")
    print("="*70 + "\n")
    
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="multi_user_cache",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    agent = Agent(
        name="assistant",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant. Give brief, accurate answers."
    )
    
    app = App(name="multi_user_app", root_agent=agent)
    cached_agent = AsyncGoogleADKCachedAgent(cache_manager, agent, app)
    
    async with cache_manager:
        # Clear any stale data from previous runs
        await cache_manager.clear()
        print("Cache cleared.\n")
        
        # Query 1: Alice asks about Ghana
        print("1. Alice asks: 'What is the capital of Ghana?'")
        response1 = await cached_agent.query(
            "What is the capital of Ghana?",
            user_id="alice"
        )
        print(f"   Response: {response1[:100]}...\n")
        
        # Query 2: Bob asks the same question (should get from cache)
        print("2. Bob asks same question (should use cache):")
        response2 = await cached_agent.query(
            "What is the capital of Ghana?",
            user_id="bob"
        )
        print(f"   Response: {response2[:100]}...\n")
        
        # Query 3: Alice asks a semantically similar question
        print("3. Alice asks similar: 'Tell me Ghana's capital city'")
        response3 = await cached_agent.query(
            "Tell me Ghana's capital city",
            user_id="alice"
        )
        print(f"   Response: {response3[:100]}...\n")
        
        print("✅ Multi-user example complete!\n")
        await cached_agent.close()


async def main():
    """Run all examples."""
    await google_adk_example()
    await multi_user_example()


if __name__ == "__main__":
    asyncio.run(main())


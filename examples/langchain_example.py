"""LangChain integration example.

Requires: pip install langchain-google-genai python-dotenv
Set GOOGLE_API_KEY in .env file before running.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig


async def langchain_example():
    """Demonstrate LangChain integration with semantic caching."""
    print("\n" + "="*70)
    print("LangChain Integration Example")
    print("="*70 + "\n")
    
    # Check for API key
    if not os.environ.get("GOOGLE_API_KEY"):
        print("⚠️  GOOGLE_API_KEY environment variable not set.")
        print("   Set it with: export GOOGLE_API_KEY='your-api-key'")
        print("   Get a key at: https://makersuite.google.com/app/apikey")
        print("\n   Skipping LangChain example.\n")
        return
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from vertector_semantic_cache.integrations import AsyncLangChainCachedLLM
    except ImportError as e:
        print(f"⚠️  Missing dependency: {e}")
        print("   Install with: pip install langchain-google-genai")
        return
    
    # Setup cache
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="langchain_cache",
        distance_threshold=0.2,
        overwrite=True,
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Setup LLM with API key from environment
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )
    
    # Create cached LLM
    cached_llm = AsyncLangChainCachedLLM(cache_manager, llm)
    
    # Test queries
    test_queries = [
        "What is the capital of Ghana?",
        "Tell me the capital city of Ghana",  # Semantically similar
    ]
    
    async with cache_manager:
        for i, query in enumerate(test_queries, 1):
            print(f"\n[Query {i}] {query}")
            try:
                response = await cached_llm.query(
                    prompt=query,
                    system_message="You are a helpful assistant. Keep responses brief.",
                    user_id="test_user"
                )
                print(f"Response: {response[:150]}...")
            except Exception as e:
                print(f"Error: {e}")
            print("-"* 70)
        
        print("\n✅ LangChain example complete!\n")


async def main():
    """Run all examples."""
    await langchain_example()


if __name__ == "__main__":
    asyncio.run(main())

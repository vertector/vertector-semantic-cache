"""LangChain integration example."""

import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI

from semantic_cache import AsyncSemanticCacheManager, CacheConfig
from semantic_cache.integrations import AsyncLangChainCachedLLM


async def langchain_example():
    """Demonstrate LangChain integration with semantic caching."""
    print("\n" + "="*70)
    print("LangChain Integration Example")
    print("="*70 + "\n")
    
    # Setup cache
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="langchain_cache",
        distance_threshold=0.2,
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Setup LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
    )
    
    # Create cached LLM
    cached_llm = AsyncLangChainCachedLLM(cache_manager, llm)
    
    # Test queries
    test_queries = [
        "What is the capital of France?",
        "Tell me the capital city of France",  # Semantically similar
        "What's the weather like in Paris?",
        "How's the weather in Paris today?",  # Semantically similar
    ]
    
    async with cache_manager:
        for i, query in enumerate(test_queries, 1):
            print(f"\n[Query {i}] {query}")
            response = await cached_llm.query(
                prompt=query,
                system_message="You are a helpful assistant.",
                user_id="test_user"
            )
            print(f"Response: {response[:100]}...")
            print("-"* 70)
        
        # Print metrics
        print("\n" + "="*70)
        print("Cache Performance Metrics")
        print("="*70)
        metrics = cache_manager.get_metrics()
        for key, value in metrics.items():
            print(f"{key}: {value}")


async def streaming_example():
    """Demonstrate streaming with caching."""
    print("\n" + "="*70)
    print("Streaming Example")
    print("="*70 + "\n")
    
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="streaming_cache",
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    cached_llm = AsyncLangChainCachedLLM(cache_manager, llm)
    
    async with cache_manager:
        print("First query (streaming from LLM):")
        async for chunk in cached_llm.stream(
            prompt="Explain Python in one sentence.",
            user_id="test_user"
        ):
            print(chunk, end="", flush=True)
        
        print("\n\nSecond query (streaming from cache):")
        async for chunk in cached_llm.stream(
            prompt="Explain Python in one sentence.",
            user_id="test_user"
        ):
            print(chunk, end="", flush=True)
        print("\n")


async def main():
    """Run all examples."""
    await langchain_example()
    await streaming_example()


if __name__ == "__main__":
    asyncio.run(main())

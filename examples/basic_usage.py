"""Basic usage example for semantic cache."""

import asyncio
from semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig, RerankerConfig


async def basic_example():
    """Demonstrate basic semantic cache usage."""
    print("\n" + "="*70)
    print("Basic Semantic Cache Example")
    print("="*70 + "\n")
    
    # Configure cache
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="basic_cache",
        ttl=3600,  # 1 hour
        distance_threshold=0.2,  # Strict similarity
        overwrite=True,  # Overwrite existing index if needed
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"  # More compatible model
        ),
    )
    
    # Use cache with context manager
    async with AsyncSemanticCacheManager(config) as cache:
        # Store some data
        await cache.store(
            prompt="What is the capital of France?",
            response="The capital of France is Paris."
        )
        
        # Check for exact match
        result = await cache.check("What is the capital of France?")
        print(f"Exact match: {result}")
        
        # Check for semantic similarity
        result = await cache.check("Tell me the capital city of France")
        print(f"Semantic match: {result}")
        
        # No match
        result = await cache.check("What is the weather in London?")
        print(f"No match: {result}")
        
        # Print metrics
        print("\n" + "-"*70)
        print("Metrics:")
        print("-"*70)
        metrics = cache.get_metrics()
        for key, value in metrics.items():
            print(f"{key}: {value}")


async def multi_tenancy_example():
    """Demonstrate multi-tenancy with user isolation."""
    print("\n" + "="*70)
    print("Multi-Tenancy Example")
    print("="*70 + "\n")
    
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="multi_tenant_cache",
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        # Store data for different users
        await cache.store(
            prompt="What is my favorite color?",
            response="Your favorite color is blue.",
            user_id="user_1"
        )
        
        await cache.store(
            prompt="What is my favorite color?",
            response="Your favorite color is red.",
            user_id="user_2"
        )
        
        # Check cache for each user
        result1 = await cache.check("What is my favorite color?", user_id="user_1")
        result2 = await cache.check("What is my favorite color?", user_id="user_2")
        result3 = await cache.check("What is my favorite color?", user_id="user_3")
        
        print(f"User 1: {result1}")
        print(f"User 2: {result2}")
        print(f"User 3 (no cache): {result3}")


async def reranking_example():
    """Demonstrate reranking for improved relevance."""
    print("\n" + "="*70)
    print("Reranking Example")
    print("="*70 + "\n")
    
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="rerank_cache",
        distance_threshold=0.3,  # More lenient for demonstration
        reranker=RerankerConfig(
            enabled=True,
            provider="huggingface",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            limit=1,
        ),
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        # Store multiple similar responses
        await cache.store(
            prompt="How do I bake a cake?",
            response="To bake a cake, mix flour, sugar, eggs, and butter, then bake at 350°F."
        )
        
        await cache.store(
            prompt="What is cake made of?",
            response="Cake is typically made from flour, sugar, eggs, butter, and leavening agents."
        )
        
        # Query with reranking
        result = await cache.check("Tell me how to make a cake")
        print(f"Best match (with reranking): {result}")
        
        # Print metrics
        metrics = cache.get_metrics()
        print(f"\nRerank operations: {metrics['rerank_operations']}")


async def main():
    """Run all examples."""
    await basic_example()
    
    # Uncomment to test multi-tenancy
    # await multi_tenancy_example()
    
    # Uncomment to test reranking (downloads large model)
    # await reranking_example()


if __name__ == "__main__":
    asyncio.run(main())

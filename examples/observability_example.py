"""Observability & Monitoring Example.

This example demonstrates the cache's built-in observability features
including L1/L2 cache tracking, context-aware caching, and tag invalidation.

Note: Metrics collection has known issues with hanging. This example
focuses on demonstrating the observable behavior through logging.
"""

import asyncio
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from vertector_semantic_cache.core.config import L1CacheConfig

async def main():
    print("\n" + "="*70)
    print("Observability & Monitoring Example")
    print("="*70 + "\n")
    
    # Configure cache with L1 cache enabled (observability via logs)
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="obs_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
        # Note: Tracing disabled to prevent console spam
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        print("="*70)
        print("PHASE 1: Testing L1/L2 Cache Behavior")
        print("="*70 + "\n")
        
        # Store and test L1/L2
        prompt = "What is machine learning?"
        response = "Machine learning is a subset of AI that enables systems to learn from data."
        
        print("1. Storing entry (goes to both L1 and L2)")
        await cache.store(prompt, response)
        
        print("\n2. First check (Should be L1 HIT - watch the logs!)")
        result = await cache.check(prompt)
        print(f"   Result: {result[:50]}...")
        
        print("\n3. Clearing L1 cache only")
        if cache._l1_cache:
            cache._l1_cache.clear()
            print("   L1 cache cleared")
        
        print("\n4. Second check (Should be L2 HIT - notice the latency difference)")
        result = await cache.check(prompt)
        print(f"   Result: {result[:50] if result else 'None'}...")
        
        print("\n5. Third check (Should be L1 HIT again - populated from L2)")
        result = await cache.check(prompt)
        print(f"   Result: {result[:50]}...")
        
        print("\n" + "="*70)
        print("PHASE 2: Context-Aware Caching")
        print("="*70 + "\n")
        
        # Store with different contexts
        await cache.store(
            "What is the best laptop?",
            "For data science, MacBook Pro M3 Max is excellent.",
            context={"user_persona": "data_scientist"}
        )
        
        await cache.store(
            "What is the best laptop?",
            "For gaming, ASUS ROG Zephyrus G14 is top tier.",
            context={"user_persona": "gamer"}
        )
        
        print("Checking with data_scientist context...")
        result = await cache.check(
            "What is the best laptop?",
            context={"user_persona": "data_scientist"}
        )
        print(f"   Result: {result}")
        
        print("\nChecking with gamer context...")
        result = await cache.check(
            "What is the best laptop?",
            context={"user_persona": "gamer"}
        )
        print(f"   Result: {result}")
        
        print("\n" + "="*70)
        print("PHASE 3: Tag-Based Invalidation")
        print("="*70 + "\n")
        
        await cache.store(
            "What is Python?",
            "Python is a high-level programming language.",
            tags=["language:python", "category:programming"]
        )
        print("Stored entry with tags: ['language:python', 'category:programming']")
        
        print("\nInvalidating by tag 'language:python'...")
        count = await cache.invalidate_by_tag("language:python")
        print(f"   Invalidated {count} entries")
        
        print("\nChecking after invalidation (should be MISS)...")
        result = await cache.check("What is Python?")
        print(f"   Result: {result}")
        
        print("\n" + "="*70)
        print("KEY OBSERVABILITY INSIGHTS")
        print("="*70 + "\n")
        
        print("✓ L1 Cache: In-memory, sub-millisecond latency")
        print("✓ L2 Cache: Redis-based, ~20-30ms latency")
        print("✓ Context-Aware: Same prompt, different responses based on context")
        print("✓ Tag Invalidation: Selective cache invalidation by tags")
        print("✓ Logging: All operations logged with timing information")
        
        print("\n✅ Observability example complete!\n")


if __name__ == "__main__":
    asyncio.run(main())

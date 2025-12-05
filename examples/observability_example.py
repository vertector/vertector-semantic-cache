"""Observability & Monitoring Example.

This example demonstrates the cache's built-in observability features
including L1/L2 cache tracking, context-aware caching, tag invalidation,
and the metrics API.
"""

import asyncio
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from vertector_semantic_cache.core.config import L1CacheConfig

async def main():
    print("\n" + "="*70)
    print("Observability & Monitoring Example")
    print("="*70 + "\n")
    
    # Configure cache with L1 cache enabled
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="obs_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
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
        
        print("\n2. First check (Should be L1 HIT)")
        result = await cache.check(prompt)
        print(f"   Result: {result[:50]}...")
        
        print("\n3. Clearing L1 cache only")
        if cache._l1_cache:
            cache._l1_cache.clear()
            print("   L1 cache cleared")
        
        print("\n4. Second check (Should be L2 HIT)")
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
        print("PHASE 4: Metrics API")
        print("="*70 + "\n")
        
        # Get detailed metrics
        metrics = cache.get_metrics()
        
        print("Overall Cache Metrics:")
        print(f"  Total Queries: {metrics['total_queries']}")
        print(f"  Cache Hits: {metrics['cache_hits']}")
        print(f"  Cache Misses: {metrics['cache_misses']}")
        print(f"  Hit Rate: {metrics['hit_rate_percentage']}%")
        print()
        
        print("L1 Cache Metrics:")
        l1 = metrics['l1_cache']
        print(f"  Hits: {l1['hits']}")
        print(f"  Misses: {l1['misses']}")
        print(f"  Hit Rate: {l1['hit_rate_percentage']}%")
        print(f"  Avg Latency: {l1['avg_latency_ms']}ms")
        print()
        
        print("L2 Cache Metrics:")
        l2 = metrics['l2_cache']
        print(f"  Hits: {l2['hits']}")
        print(f"  Misses: {l2['misses']}")
        print(f"  Hit Rate: {l2['hit_rate_percentage']}%")
        print(f"  Avg Latency: {l2['avg_latency_ms']}ms")
        print()
        
        if metrics['context_hits']:
            print("Context Hits Distribution:")
            for ctx, count in metrics['context_hits'].items():
                print(f"  {ctx}: {count}")
            print()
        
        if metrics['tag_invalidations']:
            print("Tag Invalidations:")
            for tag, count in metrics['tag_invalidations'].items():
                print(f"  {tag}: {count}")
            print()
        
        print("Staleness Tracking:")
        staleness = metrics['staleness']
        print(f"  Stale Served: {staleness['stale_served_count']}")
        print(f"  Stale Refused: {staleness['stale_refused_count']}")
        print(f"  Version Mismatches: {staleness['version_mismatches']}")
        
        print("\n" + "="*70)
        print("PHASE 5: Prometheus Export")
        print("="*70 + "\n")
        
        prometheus_metrics = cache.get_metrics_prometheus()
        # Show first 20 lines
        lines = prometheus_metrics.split('\n')[:20]
        print('\n'.join(lines))
        print(f"\n... ({len(prometheus_metrics.split(chr(10))) - 20} more lines)")
        
        print("\n✅ Observability example complete!\n")


if __name__ == "__main__":
    asyncio.run(main())

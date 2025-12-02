import asyncio
import time
from semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from semantic_cache.core.config import L1CacheConfig, ObservabilityConfig

async def main():
    print("\n" + "="*70)
    print("Observability & Monitoring Example")
    print("="*70 + "\n")
    
    # Configure cache with observability enabled
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="obs_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
        observability=ObservabilityConfig(
            enable_tracing=True,
            tracing_exporter="console",  # Use console for demo
            enable_detailed_metrics=True,
            log_performance=True,
        )
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        print("="*70)
        print("PHASE 1: Testing L1/L2 Cache Breakdown")
        print("="*70 + "\n")
        
        # Store and test L1/L2
        prompt = "What is machine learning?"
        response = "Machine learning is a subset of AI that enables systems to learn from data."
        
        print("1. Storing entry (goes to both L1 and L2)")
        await cache.store(prompt, response, context={"user_persona": "data_scientist"})
        
        print("\n2. First check (Should be L1 HIT)")
        result = await cache.check(prompt, context={"user_persona": "data_scientist"})
        print(f"   Result: {result[:50]}...")
        
        print("\n3. Clearing L1 cache only")
        if cache._l1_cache:
            cache._l1_cache.clear()
        
        print("\n4. Second check (Should be L2 HIT)")
        result = await cache.check(prompt, context={"user_persona": "data_scientist"})
        print(f"   Result: {result[:50] if result else 'None'}...")
        
        print("\n5. Third check (Should be L1 HIT again, as it was populated from L2)")
        result = await cache.check(prompt, context={"user_persona": "data_scientist"})
        print(f"   Result: {result[:50]}...")
        
        print("\n" + "="*70)
        print("PHASE 2: Testing Context-Aware Metrics")
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
        print("PHASE 3: Testing Tag-Based Invalidation Metrics")
        print("="*70 + "\n")
        
        await cache.store(
            "What is Python?",
            "Python is a high-level programming language.",
            tags=["language:python", "category:programming"]
        )
        
        print("Invalidating by tag 'language:python'...")
        count = await cache.invalidate_by_tag("language:python")
        print(f"   Invalidated {count} entries")
        
        print("\n" + "="*70)
        print("METRICS SUMMARY")
        print("="*70 + "\n")
        
        # Get detailed metrics
        metrics = cache.get_metrics()
        
        print("Overall Cache Metrics:")
        print(f"  Total Queries: {metrics['total_queries']}")
        print(f"  Overall Hit Rate: {metrics['hit_rate_percentage']}%")
        print()
        
        print("L1 Cache Metrics:")
        l1_metrics = metrics['l1_cache']
        print(f"  Hits: {l1_metrics['hits']}")
        print(f"  Misses: {l1_metrics['misses']}")
        print(f"  Hit Rate: {l1_metrics['hit_rate_percentage']}%")
        print(f"  Avg Latency: {l1_metrics['avg_latency_ms']}ms")
        print()
        
        print("L2 Cache Metrics:")
        l2_metrics = metrics['l2_cache']
        print(f"  Hits: {l2_metrics['hits']}")
        print(f"  Misses: {l2_metrics['misses']}")
        print(f"  Hit Rate: {l2_metrics['hit_rate_percentage']}%")
        print(f"  Avg Latency: {l2_metrics['avg_latency_ms']}ms")
        print()
        
        print("Context Hits Distribution:")
        for context_type, count in metrics['context_hits'].items():
            print(f"  {context_type}: {count}")
        print()
        
        print("Tag Invalidations:")
        for tag, count in metrics['tag_invalidations'].items():
            print(f"  {tag}: {count}")
        print()
        
        print("\n" + "="*70)
        print("PROMETHEUS METRICS")
        print("="*70 + "\n")
        
        # Get Prometheus format (first 40 lines)
        prometheus_metrics = cache.get_metrics_prometheus()
        lines = prometheus_metrics.split('\n')[:40]
        print('\n'.join(lines))
        print(f"\n... ({len(prometheus_metrics.split(chr(10))) - 40} more lines)")

if __name__ == "__main__":
    asyncio.run(main())

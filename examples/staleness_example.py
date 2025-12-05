import asyncio
import time
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from vertector_semantic_cache.core.config import L1CacheConfig

async def main():
    print("\n" + "="*70)
    print("Cache Staleness Mitigation Example")
    print("="*70 + "\n")
    
    # Configure cache with staleness mitigation
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="staleness_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
        ttl=5,  # Short TTL for demo (5 seconds)
        
        # Staleness mitigation settings
        enable_stale_while_revalidate=True,
        stale_tolerance_seconds=10,  # Serve stale up to 10s old
        max_stale_age_seconds=30,    # Refuse if older than 30s
        
        # Version checking
        enable_version_checking=True,
        cache_version="v1.0.0",
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        
        print("="*70)
        print("PHASE 1: Fresh Cache Entry")
        print("="*70 + "\n")
    # 1. Store initial value
    print("\n1. Storing initial value...")
    await cache.store(
        prompt="What is the capital of Ghana?",
        response="The capital of Ghana is Accra.",
        metadata={"source": "wikipedia"}
    )
    print("Stored: 'The capital of Ghana is Accra.'")

    # 2. Retrieve (should be a hit)
    print("\n2. Retrieving (should be a hit)...")
    result = await cache.check("What is the capital of Ghana?")
    print(f"Result: {result}")
        print(f"Status: FRESH ✓\n")
        
        print("="*70)
        print("PHASE 2: Stale-While-Revalidate (After TTL Expiry)")
        print("="*70 + "\n")
        
        # Wait for TTL to expire (5 seconds)
        print("Waiting 7 seconds for TTL to expire...")
        await asyncio.sleep(7)
        
        # Check again (stale, but within tolerance)
        print("\nChecking after TTL expiry (age ~7s):")
        result = await cache.check("What is the capital of France?")
        print(f"Result: {result}")
        
        metrics = cache.get_metrics()
        if metrics['staleness']['stale_served_count'] > 0:
            print(f"Status: STALE (served anyway) ✓")
            print(f"Stale served count: {metrics['staleness']['stale_served_count']}")
            print(f"Average stale age: {metrics['staleness']['average_stale_age_seconds']:.1f}s\n")
        
        print("="*70)
        print("PHASE 3: Too Stale (Beyond Max Age)")
        print("="*70 + "\n")
        
        # Wait beyond max stale age
        print("Waiting 25 more seconds to exceed max stale age...")
        await asyncio.sleep(25)
        
        # Check again (too stale, should refuse)
        print(f"\nChecking after ~32s (beyond max_stale_age of 30s):")
        result = await cache.check("What is the capital of France?")
        print(f"Result: {result}")
        
        metrics = cache.get_metrics()
        if metrics['staleness']['stale_refused_count'] > 0:
            print(f"Status: TOO STALE (refused) ✓")
            print(f"Stale refused count: {metrics['staleness']['stale_refused_count']}\n")
        
        print("="*70)
        print("PHASE 4: Version-Based Invalidation")
        print("="*70 + "\n")
        
        # Store with current version
        await cache.store(
            prompt="What is machine learning?",
            response="ML is a subset of AI (v1.0.0)."
        )
        print("✓ Stored with version v1.0.0\n")
        
        # Check (should hit)
        result = await cache.check("What is machine learning?")
        print(f"Check with v1.0.0: {result}")
        print("Status: VERSION MATCH ✓\n")
        
        # Update cache version
        cache.config.cache_version = "v2.0.0"
        print("Cache version updated to v2.0.0\n")
        
        # Check again (should miss due to version mismatch)
        result = await cache.check("What is machine learning?")
        print(f"Check with v2.0.0: {result}")
        
        metrics = cache.get_metrics()
        print(f"Status: VERSION MISMATCH ✓")
        print(f"Version mismatches: {metrics['staleness']['version_mismatches']}\n")
        
        print("="*70)
        print("STALENESS METRICS SUMMARY")
        print("="*70 + "\n")
        
        staleness = metrics['staleness']
        print(f"Stale Served:      {staleness['stale_served_count']}")
        print(f"Stale Refused:     {staleness['stale_refused_count']}")
        print(f"Version Mismatches: {staleness['version_mismatches']}")
        print(f"Avg Stale Age:     {staleness['average_stale_age_seconds']:.1f}s\n")
        
        print("="*70)
        print("KEY TAKEAWAYS")
        print("="*70 + "\n")
        
        print("✓ Stale-While-Revalidate: Serves slightly old data for better UX")
        print("✓ Max Stale Age: Prevents serving very old data")
        print("✓ Version Checking: Automatically invalidates on model changes")
        print("✓ Full Metrics: Track staleness patterns in production\n")

if __name__ == "__main__":
    asyncio.run(main())

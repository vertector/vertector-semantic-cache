import asyncio
import time
from semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from semantic_cache.core.config import L1CacheConfig

# Example: User-provided refresh callback
async def my_llm_refresh_callback(prompt: str, user_id: str = None, context: dict = None) -> str:
    """
    Example callback for refreshing stale cache entries.
    In production, this would call your actual LLM.
    """
    print(f"\n🔄 REFRESH CALLBACK: Re-generating response for '{prompt[:50]}...'")
    
    # Simulate LLM call
    await asyncio.sleep(0.5)  # Simulate API latency
    
    # Return fresh response (in production, call your LLM here)
    return f"REFRESHED: {prompt} = Fresh answer at {time.time():.0f}"

async def main():
    print("\n" + "="*70)
    print("Stale-While-Revalidate with Background Refresh Example")
    print("="*70 + "\n")
    
    # Configure cache with automatic refresh callback
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="refresh_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
        ttl=3,  # Very short TTL for demo (3 seconds)
        
        # Staleness mitigation
        enable_stale_while_revalidate=True,
        stale_tolerance_seconds=10,   # Serve stale up to 10s
        max_stale_age_seconds=30,      # Refuse if older than 30s
        
        # Background refresh callback
        stale_refresh_callback=my_llm_refresh_callback,  # <-- User callback
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        
        print("="*70)
        print("SCENARIO 1: Fresh Entry")
        print("="*70 + "\n")
        
        # Store initial entry
        await cache.store(
            prompt="What is the capital of France?",
            response="The capital of France is Paris (stored at 0s)."
        )
        print("✓ Stored fresh entry\n")
        
        # Check immediately
        result = await cache.check("What is the capital of France?")
        print(f"Check at 0s: {result[:60]}...")
        print("Status: FRESH ✓\n")
        
        print("="*70)
        print("SCENARIO 2: Stale Entry → Background Refresh Triggered")
        print("="*70 + "\n")
        
        # Wait for TTL to expire
        print("Waiting 5 seconds for entry to become stale (TTL=3s)...")
        await asyncio.sleep(5)
        
        print("\nChecking stale entry (age ~5s):")
        result = await cache.check("What is the capital of France?")
        print(f"Returned: {result[:60]}...")
        print("Status: STALE (served) + Background refresh triggered ✓")
        
        # Give background refresh time to complete
        print("\nWaiting 1 second for background refresh to complete...")
        await asyncio.sleep(1)
        
        # Check again - should have fresh data now
        print("\nChecking after background refresh:")
        result2 = await cache.check("What is the capital of France?")
        if "REFRESHED" in result2:
            print(f"Returned: {result2[:60]}...")
            print("Status: Background refresh successful! ✅\n")
        else:
            print(f"Returned: {result2[:60]}...")
            print("Status: Still has old data (refresh may still be running)\n")
        
        print("="*70)
        print("SCENARIO 3: Multiple Stale Checks → Only One Refresh")
        print("="*70 + "\n")
        
        # Store another entry
        await cache.store(
            prompt="What is machine learning?",
            response="ML is a subset of AI."
        )
        
        # Wait for it to go stale
        await asyncio.sleep(5)
        
        print("Making 3 concurrent checks of stale entry:")
        # Multiple concurrent checks
        results = await asyncio.gather(
            cache.check("What is machine learning?"),
            cache.check("What is machine learning?"),
            cache.check("What is machine learning?"),
        )
        
        print(f"All 3 returned stale data: {all(r is not None for r in results)} ✓")
        print("Note: Background refresh triggered only once (efficient!)\n")
        
        # Wait for refresh
        await asyncio.sleep(1)
        
        print("="*70)
        print("METRICS SUMMARY")
        print("="*70 + "\n")
        
        metrics = cache.get_metrics()
        staleness = metrics['staleness']
        
        print(f"Stale Served:       {staleness['stale_served_count']}")
        print(f"Stale Refused:      {staleness['stale_refused_count']}")
        print(f"Avg Stale Age:      {staleness['average_stale_age_seconds']:.1f}s")
        print(f"Total Queries:      {metrics['total_queries']}")
        print(f"Hit Rate:           {metrics['hit_rate_percentage']:.1f}%\n")
        
        print("="*70)
        print("KEY BENEFITS")
        print("="*70 + "\n")
        
        print("✅ Users get immediate response (even if slightly stale)")
        print("✅ Cache automatically refreshes in background")
        print("✅ Next user gets fresh data")
        print("✅ No manual cache management needed")
        print("✅ Configurable staleness tolerance\n")

if __name__ == "__main__":
    asyncio.run(main())

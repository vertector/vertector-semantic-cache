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
        print("1. Storing initial value...")
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
        print("Status: FRESH ✓\n")
        
        print("="*70)
        print("PHASE 2: Stale-While-Revalidate (After TTL Expiry)")
        print("="*70 + "\n")
        
        # Wait for TTL to expire (5 seconds)
        print("Waiting 7 seconds for TTL to expire...")
        await asyncio.sleep(7)
        
        # Check again (stale, but within tolerance)
        print("\nChecking after TTL expiry (age ~7s):")
        result = await cache.check("What is the capital of Ghana?")
        print(f"Result: {result}")
        print("Status: STALE (served anyway) ✓\n")
        
        print("="*70)
        print("PHASE 3: Version-Based Invalidation")
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
        print("Status: VERSION MISMATCH ✓\n")
        
        print("="*70)
        print("KEY TAKEAWAYS")
        print("="*70 + "\n")
        
        print("✓ Stale-While-Revalidate: Serves slightly old data for better UX")
        print("✓ Max Stale Age: Prevents serving very old data")
        print("✓ Version Checking: Automatically invalidates on model changes\n")

if __name__ == "__main__":
    asyncio.run(main())

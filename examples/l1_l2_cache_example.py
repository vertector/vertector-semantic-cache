import asyncio
import time
from semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from semantic_cache.core.config import L1CacheConfig

async def main():
    print("\n" + "="*70)
    print("L1/L2 Cache Hierarchy Example")
    print("="*70 + "\n")
    
    # Configure cache with L1 enabled
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="l1_l2_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(
            enabled=True,
            max_size=100,
            ttl_seconds=60,
            eviction_strategy="lru"
        )
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        prompt = "What is the speed of light?"
        response = "The speed of light is approximately 299,792,458 meters per second."
        
        print(f"1. Initial Check (Should be MISS): '{prompt}'")
        start = time.time()
        result = await cache.check(prompt)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        print(f"\n2. Storing in Cache: '{prompt}'")
        await cache.store(prompt, response)
        
        print(f"\n3. Second Check (Should be L1 HIT): '{prompt}'")
        start = time.time()
        result = await cache.check(prompt)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        # Verify it was an L1 hit by checking logs or metrics (in a real test)
        # Here we can infer from the extremely low latency
        
        print(f"\n4. Clearing Cache")
        await cache.clear()
        
        print(f"\n5. Third Check (Should be MISS): '{prompt}'")
        result = await cache.check(prompt)
        print(f"   Result: {result}")

if __name__ == "__main__":
    # Use the activation script or PYTHONPATH to run this
    # PYTHONPATH=src .venv/bin/python examples/l1_l2_cache_example.py
    asyncio.run(main())

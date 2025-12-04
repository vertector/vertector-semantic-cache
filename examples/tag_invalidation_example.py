import asyncio
import time
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from vertector_semantic_cache.core.config import L1CacheConfig

async def main():
    print("\n" + "="*70)
    print("Tag-Based Invalidation Example")
    print("="*70 + "\n")
    
    # Configure cache with tags enabled
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="tag_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
        enable_tags=True
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        prompt = "What is the price of iPhone 15?"
        response = "The iPhone 15 starts at $799."
        tags = ["product:iphone15", "category:electronics", "brand:apple"]
        
        print(f"1. Storing with tags: {tags}")
        await cache.store(prompt, response, tags=tags)
        
        print(f"\n2. Check (Should HIT)")
        start = time.time()
        result = await cache.check(prompt)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        print(f"\n3. Invalidate by tag 'product:iphone15'")
        count = await cache.invalidate_by_tag("product:iphone15")
        print(f"   Invalidated count: {count}")
        
        print(f"\n4. Check (Should MISS)")
        start = time.time()
        result = await cache.check(prompt)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        # Test bulk invalidation
        print(f"\n5. Storing again")
        await cache.store(prompt, response, tags=tags)
        
        print(f"\n6. Invalidate by multiple tags (brand:apple OR category:books)")
        # Should match brand:apple
        count = await cache.invalidate_by_tags(["brand:apple", "category:books"])
        print(f"   Invalidated count: {count}")
        
        print(f"\n7. Check (Should MISS)")
        result = await cache.check(prompt)
        print(f"   Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())

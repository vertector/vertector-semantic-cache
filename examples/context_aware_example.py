import asyncio
import time
from semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig
from semantic_cache.core.config import L1CacheConfig

async def main():
    print("\n" + "="*70)
    print("Context-Aware Caching Example")
    print("="*70 + "\n")
    
    # Configure cache with context hashing enabled
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="context_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
        enable_context_hashing=True,
        context_fields=["user_persona", "conversation_id"]
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        prompt = "What is the best laptop?"
        
        # Context A: Gamer
        context_gamer = {"user_persona": "gamer", "budget": "high"}
        response_gamer = "For gaming, the ASUS ROG Zephyrus G14 is excellent."
        
        # Context B: Developer
        context_dev = {"user_persona": "developer", "budget": "high"}
        response_dev = "For development, the MacBook Pro M3 Max is top tier."
        
        print(f"1. Storing for Gamer Context")
        await cache.store(prompt, response_gamer, context=context_gamer)
        
        print(f"\n2. Check Gamer Context (Should HIT)")
        start = time.time()
        result = await cache.check(prompt, context=context_gamer)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        print(f"\n3. Check Developer Context (Should MISS)")
        start = time.time()
        result = await cache.check(prompt, context=context_dev)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        print(f"\n4. Storing for Developer Context")
        await cache.store(prompt, response_dev, context=context_dev)
        
        print(f"\n5. Check Developer Context (Should HIT)")
        start = time.time()
        result = await cache.check(prompt, context=context_dev)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")
        
        print(f"\n6. Check Gamer Context Again (Should HIT)")
        start = time.time()
        result = await cache.check(prompt, context=context_gamer)
        print(f"   Result: {result}")
        print(f"   Time: {(time.time() - start)*1000:.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())

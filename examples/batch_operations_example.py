import asyncio
import time
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig, VectorizerConfig

async def main():
    print("\n" + "="*70)
    print("Batch Operations Performance Example")
    print("="*70 + "\n")
    
    # Configure cache
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="batch_demo",
        overwrite=True,
        vectorizer=VectorizerConfig(
            provider="huggingface",
            model="sentence-transformers/all-MiniLM-L6-v2"
        ),
        l1_cache=L1CacheConfig(enabled=True),
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        # Sample prompts for testing
        prompts = [
            "What is artificial intelligence?",
            "What is machine learning?",
            "What is deep learning?",
            "What is neural network?",
            "What is natural language processing?",
            "What is computer vision?",
            "What is reinforcement learning?",
            "What is supervised learning?",
            "What is unsupervised learning?",
            "What is transfer learning?",
        ]
        
        responses = [
            "AI is the simulation of human intelligence in machines.",
            "ML is a subset of AI that enables systems to learn from data.",
            "DL is a subset of ML using neural networks with multiple layers.",
            "A neural network is a computing system inspired by biological neural networks.",
            "NLP is a field of AI focused on interaction between computers and human language.",
            "Computer vision is AI that enables computers to interpret visual information.",
            "RL is learning through interaction with an environment to maximize rewards.",
            "Supervised learning uses labeled data to train models.",
            "Unsupervised learning finds patterns in unlabeled data.",
            "Transfer learning applies knowledge from one domain to another.",
        ]
        
        print("="*70)
        print("PHASE 1: Storing 10 entries")
        print("="*70 + "\n")
        
        # Store entries
        store_start = time.time()
        for prompt, response in zip(prompts, responses):
            await cache.store(prompt, response)
        store_time = time.time() - store_start
        print(f"Stored 10 entries in {store_time*1000:.2f}ms\n")
        
        print("="*70)
        print("PHASE 2: Sequential vs Batch Check Comparison")
        print("="*70 + "\n")
        
        # Clear L1 to ensure fair comparison
        if cache._l1_cache:
            cache._l1_cache.clear()
        
        # Sequential check
        print("1. Sequential Check (calling check() 10 times):")
        seq_start = time.time()
        seq_results = []
        for prompt in prompts:
            result = await cache.check(prompt)
            seq_results.append(result)
        seq_time = time.time() - seq_start
        seq_hits = sum(1 for r in seq_results if r)
        print(f"   Time: {seq_time*1000:.2f}ms")
        print(f"   Hits: {seq_hits}/{len(prompts)}")
        print(f"   Avg per query: {seq_time*1000/len(prompts):.2f}ms\n")
        
        # Clear L1 again for fair comparison
        if cache._l1_cache:
            cache._l1_cache.clear()
        
        # Batch check
        print("2. Batch Check (calling batch_check() once):")
        batch_start = time.time()
        batch_results = await cache.batch_check(prompts)
        batch_time = time.time() - batch_start
        batch_hits = sum(1 for r in batch_results if r)
        print(f"   Time: {batch_time*1000:.2f}ms")
        print(f"   Hits: {batch_hits}/{len(prompts)}")
        print(f"   Avg per query: {batch_time*1000/len(prompts):.2f}ms\n")
        
        # Performance improvement
        speedup = seq_time / batch_time if batch_time > 0 else 0
        print(f"📊 Performance Improvement: {speedup:.1f}x faster\n")
        
        print("="*70)
        print("PHASE 3: Testing with L1 Cache (Second Run)")
        print("="*70 + "\n")
        
        # Batch check again (should all be L1 hits)
        print("Batch check with L1 cache populated:")
        l1_start = time.time()
        l1_results = await cache.batch_check(prompts)
        l1_time = time.time() - l1_start
        l1_hits = sum(1 for r in l1_results if r)
        print(f"   Time: {l1_time*1000:.2f}ms")
        print(f"   Hits: {l1_hits}/{len(prompts)}")
        print(f"   Avg per query: {l1_time*1000/len(prompts):.2f}ms")
        print(f"   L1 speedup: {seq_time/l1_time:.1f}x faster than sequential\n")
        
        print("="*70)
        print("PHASE 4: Testing with Mixed Results (Some Misses)")
        print("="*70 + "\n")
        
        # Mix of existing and new prompts
        mixed_prompts = [
            "What is artificial intelligence?",  # Exists
            "This is a brand new prompt that doesn't exist",  # Miss
            "What is machine learning?",  # Exists
            "Another new prompt",  # Miss
            "What is deep learning?",  # Exists
        ]
        
        print("Batch check with mixed hits/misses:")
        mixed_start = time.time()
        mixed_results = await cache.batch_check(mixed_prompts)
        mixed_time = time.time() - mixed_start
        mixed_hits = sum(1 for r in mixed_results if r)
        print(f"   Time: {mixed_time*1000:.2f}ms")
        print(f"   Hits: {mixed_hits}/{len(mixed_prompts)}")
        print(f"   Misses: {len(mixed_prompts) - mixed_hits}/{len(mixed_prompts)}")
        print(f"   Results: {['HIT' if r else 'MISS' for r in mixed_results]}\n")
        
        print("="*70)
        print("PERFORMANCE SUMMARY")
        print("="*70 + "\n")
        
        print(f"Sequential (10 prompts):  {seq_time*1000:.2f}ms ({seq_time*1000/len(prompts):.2f}ms/query)")
        print(f"Batch (10 prompts):       {batch_time*1000:.2f}ms ({batch_time*1000/len(prompts):.2f}ms/query)")
        print(f"Batch with L1 (10 prompts): {l1_time*1000:.2f}ms ({l1_time*1000/len(prompts):.2f}ms/query)")
        print(f"\n🚀 Speedup: {speedup:.1f}x faster with batch operations")
        print(f"⚡ With L1: {seq_time/l1_time:.1f}x faster overall\n")
        
        # Get metrics
        metrics = cache.get_metrics()
        print("Cache Metrics:")
        print(f"  Total Queries: {metrics['total_queries']}")
        print(f"  Overall Hit Rate: {metrics['hit_rate_percentage']}%")
        print(f"  L1 Hit Rate: {metrics['l1_cache']['hit_rate_percentage']}%")
        print(f"  L2 Hit Rate: {metrics['l2_cache']['hit_rate_percentage']}%")

if __name__ == "__main__":
    asyncio.run(main())

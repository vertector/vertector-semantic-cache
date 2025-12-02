# Advanced Caching Strategies

This document covers the advanced caching features implemented in semantic-cache for enterprise-grade performance and scalability.

## Table of Contents

- [L1/L2 Cache Hierarchy](#l1l2-cache-hierarchy)
- [Context-Aware Caching](#context-aware-caching)
- [Tag-Based Invalidation](#tag-based-invalidation)
- [Observability & Monitoring](#observability--monitoring)

---

## L1/L2 Cache Hierarchy

The semantic cache implements a two-tier caching architecture for optimal performance:

- **L1 Cache (In-Memory)**: Ultra-fast lookups (<1ms) using `cachetools`
- **L2 Cache (Redis)**: Persistent vector store with semantic search (~20ms)

### Configuration

```python
from semantic_cache import CacheConfig
from semantic_cache.core.config import L1CacheConfig

config = CacheConfig(
    redis_url="redis://localhost:6380",
    l1_cache=L1CacheConfig(
        enabled=True,              # Enable L1 cache
        max_size=1000,             # Max entries in memory
        ttl_seconds=300,           # 5 minutes TTL
        eviction_strategy="lru"    # "lru", "lfu", or "ttl"
    )
)
```

### Eviction Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| **LRU** (Least Recently Used) | Evicts entries not accessed recently | General purpose, temporal locality |
| **LFU** (Least Frequently Used) | Evicts entries accessed least often | Popular queries, high reuse |
| **TTL** (Time To Live) | Evicts entries based on age | Time-sensitive data |

### How It Works

1. **Cache Check Flow**:
   ```
   Query → L1 Check → L1 Hit? → Return (0.01-0.1ms)
                    ↓ L1 Miss
                    L2 Check → L2 Hit? → Populate L1 → Return (10-30ms)
                              ↓ L2 Miss
                              Return None
   ```

2. **Write-Through Strategy**:
   - All writes go to **both** L1 and L2
   - Ensures consistency across layers
   - TTL respected in both caches

3. **Automatic L1 Population**:
   - L2 hits automatically populate L1
   - Frequently accessed data migrates to L1
   - Optimal performance without manual tuning

### Performance Characteristics

| Operation | L1 Cache | L2 Cache | Improvement |
|-----------|----------|----------|-------------|
| **Latency** | 0.01-0.1ms | 10-30ms | **100-1000x faster** |
| **Throughput** | 10,000+ QPS | 500-1000 QPS | **10-20x higher** |
| **Capacity** | Limited (memory) | Large (Redis) | Trade-off |

### Example

```python
import asyncio
from semantic_cache import AsyncSemanticCacheManager, CacheConfig
from semantic_cache.core.config import L1CacheConfig

async def main():
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        l1_cache=L1CacheConfig(
            enabled=True,
            max_size=500,
            eviction_strategy="lru"
        )
    )
    
    async with AsyncSemanticCacheManager(config) as cache:
        # Store
        await cache.store("What is AI?", "AI is...")
        
        # First check - L1 hit (0.05ms)
        result = await cache.check("What is AI?")
        
        # Clear L1
        cache._l1_cache.clear()
        
        # Second check - L2 hit, populates L1 (20ms)
        result = await cache.check("What is AI?")
        
        # Third check - L1 hit again (0.05ms)
        result = await cache.check("What is AI?")

asyncio.run(main())
```

---

## Context-Aware Caching

Context-aware caching isolates cache entries based on conversational context, ensuring users only see relevant cached responses.

### Use Cases

- **Multi-user applications**: Different users get different responses
- **Conversation context**: Same query, different answers based on conversation state
- **User personas**: Tailor responses to user roles (developer, manager, etc.)
- **Session isolation**: Separate cache per session

### Configuration

```python
config = CacheConfig(
    enable_context_hashing=True,  # Enabled by default
    context_fields=[               # Fields to include in context hash
        "conversation_id",
        "user_persona",
        "session_id"
    ]
)
```

### How It Works

1. **Context Hashing**:
   ```python
   # Context is hashed to create unique cache keys
   context = {"user_persona": "developer", "conversation_id": "conv_123"}
   
   # Generates key: prompt:user:user_id:ctx:<hash>
   context_hash = sha256(json.dumps(context, sort_keys=True))[:16]
   ```

2. **L1 Isolation**:
   - L1 cache keys include context hash
   - Different contexts = different L1 entries

3. **L2 Filtering**:
   - Context hash stored in RedisVL metadata
   - Retrieval filters by context_hash field

### Example

```python
async with AsyncSemanticCacheManager(config) as cache:
    # Store for developer persona
    await cache.store(
        prompt="What is the best laptop?",
        response="For coding, MacBook Pro M3 Max is excellent.",
        context={"user_persona": "developer"}
    )
    
    # Store for gamer persona
    await cache.store(
        prompt="What is the best laptop?",
        response="For gaming, ASUS ROG Zephyrus G14 is top tier.",
        context={"user_persona": "gamer"}
    )
    
    # Check with developer context
    result = await cache.check(
        "What is the best laptop?",
        context={"user_persona": "developer"}
    )
    # Returns: "For coding, MacBook Pro M3 Max is excellent."
    
    # Check with gamer context
    result = await cache.check(
        "What is the best laptop?",
        context={"user_persona": "gamer"}
    )
    # Returns: "For gaming, ASUS ROG Zephyrus G14 is top tier."
```

### Context Fields

You can customize which fields are included in the context hash:

```python
config = CacheConfig(
    context_fields=["user_id", "tenant_id", "language"]
)

# Only these fields will be hashed
context = {
    "user_id": "user_123",
    "tenant_id": "tenant_456",
    "language": "en",
    "other_field": "ignored"  # Not hashed
}
```

---

## Tag-Based Invalidation

Tag-based invalidation allows flexible cache management by associating tags with cache entries and invalidating by tag patterns.

### Use Cases

- **Product updates**: Invalidate all caches related to a product
- **Category changes**: Clear cache for entire categories
- **Brand updates**: Invalidate by brand
- **Bulk operations**: Invalidate multiple related entries at once

### Configuration

```python
config = CacheConfig(
    enable_tags=True,           # Enabled by default
    max_tags_per_entry=10       # Max tags per cache entry
)
```

### Tagging Entries

```python
# Store with multiple tags
await cache.store(
    prompt="What is the price of iPhone 15?",
    response="The iPhone 15 starts at $799.",
    tags=[
        "product:iphone15",
        "category:electronics",
        "brand:apple",
        "type:smartphone"
    ]
)
```

### Invalidation Methods

#### 1. Single Tag Invalidation

```python
# Invalidate all entries with tag "product:iphone15"
count = await cache.invalidate_by_tag("product:iphone15")
print(f"Invalidated {count} entries")
```

#### 2. Multiple Tags (OR Logic)

```python
# Invalidate entries with ANY of these tags
count = await cache.invalidate_by_tags([
    "brand:apple",
    "brand:samsung"
])
# Clears all Apple OR Samsung products
```

#### 3. Multiple Tags (AND Logic)

```python
# Invalidate entries with ALL of these tags
count = await cache.invalidate_by_tags(
    ["brand:apple", "category:electronics"],
    match_all=True
)
# Only clears entries that are BOTH Apple AND Electronics
```

### Tag Naming Conventions

Best practices for tag naming:

```python
# Hierarchical tags
"category:electronics:smartphones:iphone"

# Namespace tags
"product:12345"
"brand:apple"
"vendor:acme"

# Temporal tags
"release:2024-q1"
"campaign:black-friday"

# Attribute tags
"price-range:high"
"rating:5-star"
```

### Architecture

```
┌─────────────────┐
│  Cache Entry    │
│  key: abc123    │
└────────┬────────┘
         │
         ├─────► tag:product:iphone15 → Set{abc123, def456}
         ├─────► tag:category:electronics → Set{abc123, xyz789}
         └─────► tag:brand:apple → Set{abc123, def456, ghi012}
```

When invalidating by tag, the system:
1. Looks up cache keys in the tag's set
2. Deletes all cache entries
3. Clears L1 cache for consistency

### Example: E-commerce Cache Management

```python
async with AsyncSemanticCacheManager(config) as cache:
    # Cache product queries with tags
    await cache.store(
        "iPhone 15 specs",
        "6.1-inch display, A17 chip...",
        tags=["product:iphone15", "brand:apple", "category:phones"]
    )
    
    await cache.store(
        "MacBook Pro specs",
        "14-inch, M3 Max chip...",
        tags=["product:macbook-pro", "brand:apple", "category:laptops"]
    )
    
    # Product update - invalidate specific product
    await cache.invalidate_by_tag("product:iphone15")
    
    # Brand update - invalidate all Apple products
    await cache.invalidate_by_tag("brand:apple")
    
    # Category update - invalidate all phones
    await cache.invalidate_by_tag("category:phones")
```

---

## Observability & Monitoring

Comprehensive observability features for production monitoring and debugging.

### Features

1. **Enhanced Metrics** (Enabled by default)
   - L1/L2 hit/miss breakdown
   - Latency tracking
   - Context distribution
   - Tag invalidation metrics

2. **Distributed Tracing** (Optional)
   - OpenTelemetry integration
   - End-to-end request tracing
   - Performance bottleneck identification

### Enhanced Metrics

#### Accessing Metrics

```python
metrics = cache.get_metrics()

# Overall metrics
print(f"Total Queries: {metrics['total_queries']}")
print(f"Overall Hit Rate: {metrics['hit_rate_percentage']}%")

# L1 Cache metrics
l1 = metrics['l1_cache']
print(f"L1 Hits: {l1['hits']}")
print(f"L1 Hit Rate: {l1['hit_rate_percentage']}%")
print(f"L1 Avg Latency: {l1['avg_latency_ms']}ms")

# L2 Cache metrics
l2 = metrics['l2_cache']
print(f"L2 Hits: {l2['hits']}")
print(f"L2 Hit Rate: {l2['hit_rate_percentage']}%")
print(f"L2 Avg Latency: {l2['avg_latency_ms']}ms")

# Context distribution
for context_type, count in metrics['context_hits'].items():
    print(f"Context '{context_type}': {count} hits")

# Tag invalidations
for tag, count in metrics['tag_invalidations'].items():
    print(f"Tag '{tag}': {count} invalidations")
```

#### Prometheus Export

```python
# Get Prometheus-formatted metrics
prometheus_metrics = cache.get_metrics_prometheus()

# Example output:
# semantic_cache_l1_hits_total 42
# semantic_cache_l1_misses_total 8
# semantic_cache_l1_hit_rate 84.0
# semantic_cache_l1_latency_ms 0.052
# ...
```

### Distributed Tracing

#### Setup

1. **Install OpenTelemetry dependencies**:
   ```bash
   pip install semantic-cache[observability]
   ```

2. **Configure tracing**:
   ```python
   from semantic_cache.core.config import ObservabilityConfig
   
   config = CacheConfig(
       observability=ObservabilityConfig(
           enable_tracing=True,
           tracing_exporter="jaeger",  # or "otlp", "console"
           tracing_endpoint="http://localhost:14268",
           service_name="my-app-cache"
       )
   )
   ```

#### Exporters

| Exporter | Use Case | Endpoint |
|----------|----------|----------|
| **console** | Development, debugging | stdout |
| **jaeger** | Jaeger UI | `http://localhost:14268` |
| **otlp** | OpenTelemetry Collector | `http://localhost:4317` |

#### What Gets Traced

Each cache operation creates spans with:

- **Operation**: `cache.check`, `cache.store`, `cache.invalidate_by_tag`
- **Attributes**:
  - `cache.prompt_length`
  - `cache.user_id`
  - `cache.has_context`
  - `cache_hit` (true/false)
  - `cache_layer` (L1/L2)
  - `latency_ms`
  - `l1_latency_ms` / `l2_latency_ms`

#### Example: Jaeger Setup

```bash
# Start Jaeger (Docker)
docker run -d --name jaeger \
  -p 14268:14268 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# Run your app with tracing enabled
# View traces at http://localhost:16686
```

### Grafana Dashboard

The Prometheus metrics can be visualized in Grafana. Example queries:

```promql
# Overall hit rate
rate(semantic_cache_hits_total[5m]) / rate(semantic_cache_queries_total[5m]) * 100

# L1 vs L2 hit rate comparison
rate(semantic_cache_l1_hits_total[5m])
rate(semantic_cache_l2_hits_total[5m])

# Average latency by layer
semantic_cache_l1_latency_ms
semantic_cache_l2_latency_ms

# Context distribution
sum by (context_type) (semantic_cache_context_hits_total)
```

### Configuration Reference

```python
class ObservabilityConfig(BaseModel):
    # Tracing
    enable_tracing: bool = False
    tracing_exporter: Literal["console", "otlp", "jaeger"] = "console"
    tracing_endpoint: Optional[str] = None
    service_name: str = "semantic-cache"
    
    # Metrics
    enable_detailed_metrics: bool = True  # ✅ ON by default
    metrics_prefix: str = "semantic_cache"
    
    # Logging
    enable_correlation_id: bool = True
    log_performance: bool = False
```

---

## Performance Best Practices

### 1. L1 Cache Sizing

- **Small apps** (< 100 concurrent users): 500-1000 entries
- **Medium apps** (100-1000 users): 1000-5000 entries
- **Large apps** (> 1000 users): 5000-10000 entries

### 2. Context Fields

- Only hash **necessary** fields
- Fewer fields = better L1 hit rate
- Balance between isolation and efficiency

### 3. Tags

- Use hierarchical tags for flexibility
- Limit to 5-10 tags per entry
- Consistent naming conventions

### 4. Monitoring

- Monitor L1/L2 hit rates separately
- Set alerts for:
  - Overall hit rate < 60%
  - L1 hit rate < 70%
  - Latency > 50ms (95th percentile)

---

## Migration Guide

### From Basic to L1/L2

```python
# Before
config = CacheConfig(redis_url="redis://localhost:6380")

# After
config = CacheConfig(
    redis_url="redis://localhost:6380",
    l1_cache=L1CacheConfig(enabled=True)
)
```

### Adding Context Awareness

```python
# Before
await cache.check("What is AI?", user_id="user_123")

# After
await cache.check(
    "What is AI?",
    user_id="user_123",
    context={"persona": "developer", "level": "senior"}
)
```

### Adding Tags

```python
# Before
await cache.store(prompt, response)

# After
await cache.store(
    prompt,
    response,
    tags=["category:ai", "level:beginner"]
)
```

---

## Troubleshooting

### L1 Cache Not Working

**Symptom**: All hits show as L2
**Solution**: Ensure `l1_cache.enabled=True`

```python
config = CacheConfig(
    l1_cache=L1CacheConfig(enabled=True)  # Must be True!
)
```

### Context Isolation Not Working

**Symptom**: Different contexts return same response
**Solution**: Check context fields configuration

```python
# Ensure context_hashing is enabled
config = CacheConfig(enable_context_hashing=True)

# Verify you're passing context
await cache.check(prompt, context={"persona": "dev"})
```

### Tags Not Invalidating

**Symptom**: `invalidate_by_tag()` returns 0
**Solution**: Ensure tags were stored

```python
# Store WITH tags
await cache.store(prompt, response, tags=["my-tag"])

# Then invalidate
count = await cache.invalidate_by_tag("my-tag")  # Should return > 0
```

---

## See Also

- [README.md](../README.md) - Getting started guide
- [Examples](../examples/) - Code examples
- [API Reference](API.md) - Full API documentation

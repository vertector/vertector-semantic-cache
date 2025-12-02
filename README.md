# Semantic Cache

Enterprise-grade async semantic caching for AI agents using RedisVL.

## Features

- ✨ **Full Async Support** - Built with `async/await` for non-blocking operations
- 🎯 **Semantic Similarity** - Cache responses based on meaning, not exact matches
- ⚡- **L1/L2 Cache Hierarchy**: In-memory (L1) + Redis (L2) for 10-1000x performance
- **Context-Aware Caching**: Isolate cache by user, conversation, or custom context
- **Tag-Based Invalidation**: Efficiently invalidate related entries (e.g., by product, category)
- **Batch Operations**: Check/store multiple prompts efficiently
- **Cache Staleness Mitigation**: Version-based invalidation and stale-while-revalidate with refresh callbacks
- **Observability**: Enhanced metrics (L1/L2 breakdown, staleness tracking), OpenTelemetry tracing, Prometheus export
- **Reranking**: Optional semantic reranking (HuggingFace, Cohere)
- **Async-First**: Built on asyncio for high concurrency
- **Production-Ready**: Comprehensive error handling, retries, logging
- 👥 **Multi-Tenancy** - User isolation with filterable fields
- 🔌 **Easy Integration** - Async wrappers for LangChain and Google ADK
- 📊 **Prometheus Metrics** - Export metrics for monitoring
- 📈 **Enhanced Observability** - L1/L2 metrics breakdown, context tracking, distributed tracing
- 🛡️ **Type Safe** - Full type hints with Pydantic validation

## Installation

```bash
# Basic installation
pip install semantic-cache

# With LangChain support
pip install semantic-cache[langchain]

# With Google ADK support
pip install semantic-cache[google-adk]

# With observability (OpenTelemetry tracing)
pip install semantic-cache[observability]

# With all optional dependencies
pip install semantic-cache[all]
```

## Quick Start

### Basic Usage

```python
import asyncio
from semantic_cache import AsyncSemanticCacheManager, CacheConfig

async def main():
    # Configure cache
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="my_cache",
        ttl=3600,  # 1 hour
        distance_threshold=0.2,  # Semantic similarity threshold
    )
    
    # Use cache with context manager
    async with AsyncSemanticCacheManager(config) as cache:
        # Store a response
        await cache.store(
            prompt="What is the capital of France?",
            response="The capital of France is Paris."
        )
        
        # Check for semantic match
        result = await cache.check("Tell me the capital city of France")
        print(result)  # "The capital of France is Paris."
        
        # View metrics
        metrics = cache.get_metrics()
        print(f"Hit rate: {metrics['hit_rate_percentage']}%")

asyncio.run(main())
```

### LangChain Integration

```python
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from semantic_cache import AsyncSemanticCacheManager, CacheConfig
from semantic_cache.integrations import AsyncLangChainCachedLLM

async def main():
    # Setup cache
    cache_config = CacheConfig(redis_url="redis://localhost:6380")
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Setup LLM with caching
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    cached_llm = AsyncLangChainCachedLLM(cache_manager, llm)
    
    async with cache_manager:
        # First call - hits LLM
        response1 = await cached_llm.query(
            prompt="What is the capital of France?",
            system_message="You are a helpful assistant."
        )
        
        # Second call - hits cache
        response2 = await cached_llm.query(
            prompt="Tell me the capital city of France",  # Semantically similar
            system_message="You are a helpful assistant."
        )

asyncio.run(main())
```

### Google ADK Integration

```python
import asyncio
from google.adk.agents import Agent
from google.adk.apps.app import App
from semantic_cache import AsyncSemanticCacheManager, CacheConfig
from semantic_cache.integrations import AsyncGoogleADKCachedAgent

async def main():
    # Setup cache
    cache_config = CacheConfig(redis_url="redis://localhost:6380")
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Setup agent
    agent = Agent(
        name="my_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant."
    )
    app = App(name="my_app", root_agent=agent)
    
    # Create cached agent
    cached_agent = AsyncGoogleADKCachedAgent(cache_manager, agent, app)
    
    async with cache_manager:
        response = await cached_agent.query(
            prompt="What is the capital of France?",
            user_id="user123"
        )
        print(response)

asyncio.run(main())
```

## Configuration

### Using Environment Variables

Create a `.env` file:

```env
SEMANTIC_CACHE_REDIS_URL=redis://localhost:6380
SEMANTIC_CACHE_CACHE_NAME=my_cache
SEMANTIC_CACHE_TTL=3600
SEMANTIC_CACHE_DISTANCE_THRESHOLD=0.2
SEMANTIC_CACHE_LOG_LEVEL=INFO
```

Then use `CacheSettings`:

```python
from semantic_cache.core.config import CacheSettings

settings = CacheSettings()
config = settings.to_cache_config()
```

### Vectorizer Configuration

```python
from semantic_cache import CacheConfig, VectorizerConfig

config = CacheConfig(
    vectorizer=VectorizerConfig(
        provider="openai",  # or "huggingface", "cohere", "vertexai", "voyageai"
        model="text-embedding-ada-002",
        api_config={"api_key": "your-api-key"}
    )
)
```

### Reranker Configuration

```python
from semantic_cache import CacheConfig, RerankerConfig

config = CacheConfig(
    reranker=RerankerConfig(
        enabled=True,
        provider="huggingface",  # or "cohere", "voyageai"
        model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        limit=3,
    )
)
```

## Advanced Caching Strategies

### L1/L2 Cache Hierarchy

Enable in-memory L1 caching for ultra-fast lookups (<1ms vs ~20ms for Redis):

```python
from semantic_cache import CacheConfig
from semantic_cache.core.config import L1CacheConfig

config = CacheConfig(
    redis_url="redis://localhost:6380",
    l1_cache=L1CacheConfig(
        enabled=True,
        max_size=1000,           # Max entries in L1
        ttl_seconds=300,          # 5 minutes
        eviction_strategy="lru"   # "lru", "lfu", or "ttl"
    )
)
```

**Performance:**
- L1 Cache (In-Memory): <1ms
- L2 Cache (Redis): ~20ms

### Context-Aware Caching

Isolate cache entries by context (user persona, conversation, session):

```python
# Store with context
await cache.store(
    prompt="What is the best laptop?",
    response="For gaming, the ASUS ROG Zephyrus G14 is excellent.",
    context={"user_persona": "gamer", "conversation_id": "conv_123"}
)

# Check with context - only matches same context
result = await cache.check(
    prompt="What is the best laptop?",
    context={"user_persona": "gamer", "conversation_id": "conv_123"}
)
```

**Features:**
- Automatic context hashing for deterministic keys
- L1 and L2 isolation
- Configurable context fields

### Tag-Based Invalidation

Tag cache entries for flexible invalidation:

```python
# Store with tags
await cache.store(
    prompt="What is the price of iPhone 15?",
    response="The iPhone 15 starts at $799.",
    tags=["product:iphone15", "category:electronics", "brand:apple"]
)

# Invalidate by single tag
count = await cache.invalidate_by_tag("product:iphone15")

# Invalidate by multiple tags (OR logic)
count = await cache.invalidate_by_tags(["brand:apple", "category:electronics"])

# Invalidate by multiple tags (AND logic)
count = await cache.invalidate_by_tags(
    ["brand:apple", "category:electronics"],
    match_all=True
)
```

### Batch Operations

Check or store multiple prompts efficiently with a single API call:

```python
# Batch check multiple prompts
prompts = [
    "What is AI?",
    "What is ML?",
    "What is DL?"
]

results = await cache.batch_check(prompts)
# Returns: [response1, response2, None]  # One cache miss

# With context
contexts = [
    {"user_persona": "developer"},
    {"user_persona": "developer"},
    {"user_persona": "manager"}
]
results = await cache.batch_check(prompts, contexts=contexts)
```

**Benefits:**
- Simplified API for bulk operations
- Parallel L1 cache lookups
- Concurrent L2 queries
- Automatic metrics tracking

> **Note:** Current performance is limited by RedisVL's lack of batch embedding API. Performance gains are primarily from L1 cache hits (~2-3x faster). Full 5-10x speedup awaits RedisVL batch API support.

### Cache Staleness Mitigation

Prevent serving outdated data with automatic staleness detection and refresh:

```python
# Example: Refresh callback for automatic cache updates
async def refresh_llm_response(prompt, user_id=None, context=None):
    """Called when stale data is served - refresh in background."""
    fresh_response = await your_llm.generate(prompt)
    return fresh_response

config = CacheConfig(
    ttl=3600,  # 1 hour TTL
    
    # Stale-while-revalidate (serve stale while refreshing)
    enable_stale_while_revalidate=True,
    stale_tolerance_seconds=300,       # Serve stale up to 5min old
    max_stale_age_seconds=3600,        # Refuse if older than 1hr
    stale_refresh_callback=refresh_llm_response,  # Auto-refresh
    
    # Version-based invalidation
    enable_version_checking=True,
    cache_version="v1.0.0",  # Bump to invalidate all entries
)

async with AsyncSemanticCacheManager(config) as cache:
    # Entry serves stale data briefly while refreshing in background
    result = await cache.check(prompt)
    
    # Check staleness metrics
    metrics = cache.get_metrics()
    print(f"Stale served: {metrics['staleness']['stale_served_count']}")
    print(f"Version mismatches: {metrics['staleness']['version_mismatches']}")
```

**Features:**
- **Stale-While-Revalidate**: Serve slightly stale data for better UX while refreshing
- **Background Refresh**: Optional callback to automatically update stale entries
- **Version Checking**: Auto-invalidate all entries on model/data version change
- **Staleness Metrics**: Track stale serve/refuse rates, version mismatches
- **Max Age Protection**: Refuse very old entries (configurable threshold)

> **Note:** Staleness checking works on entries still in Redis. Once Redis TTL expires and deletes an entry, it becomes a cache miss. Use longer TTLs with staleness checking for best results.

### Observability & Monitoring

Get deep insights into cache performance with automatic metrics tracking:

```python
# Enhanced metrics are enabled by default
metrics = cache.get_metrics()

print(f"Overall Hit Rate: {metrics['hit_rate_percentage']}%")
print(f"L1 Hit Rate: {metrics['l1_cache']['hit_rate_percentage']}%")
print(f"L2 Hit Rate: {metrics['l2_cache']['hit_rate_percentage']}%")
print(f"L1 Avg Latency: {metrics['l1_cache']['avg_latency_ms']}ms")
print(f"L2 Avg Latency: {metrics['l2_cache']['avg_latency_ms']}ms")

# Context distribution
for context_type, count in metrics['context_hits'].items():
    print(f"Context {context_type}: {count} hits")

# Prometheus export for monitoring
prometheus_metrics = cache.get_metrics_prometheus()
```

**Optional: Distributed Tracing**

Enable OpenTelemetry tracing for deep observability:

```python
from semantic_cache.core.config import ObservabilityConfig

config = CacheConfig(
    observability=ObservabilityConfig(
        enable_tracing=True,
        tracing_exporter="jaeger",  # or "otlp", "console"
        tracing_endpoint="http://localhost:14268",
    )
)
```

**Metrics Available:**
- L1/L2 cache hit/miss rates and latencies
- Context-based hit distribution
- Tag invalidation tracking
- Full Prometheus export for Grafana dashboards

## Advanced Features

### Multi-Tenancy

```python
# Store with user ID
await cache.store(
    prompt="What is my favorite color?",
    response="Your favorite color is blue.",
    user_id="user_1"
)

# Check with user ID
result = await cache.check(
    prompt="What is my favorite color?",
    user_id="user_1"
)
```

### Metrics Export

```python
# Get metrics as dictionary
metrics = cache.get_metrics()

# Get Prometheus format
prometheus_metrics = cache.get_metrics_prometheus()
print(prometheus_metrics)
```

### Custom Metadata

```python
await cache.store(
    prompt="What is the weather?",
    response="It's sunny.",
    metadata={
        "source": "weather_api",
        "confidence": 0.95,
        "timestamp": "2025-01-01T00:00:00Z"
    }
)
```

## Requirements

- Python >= 3.10
- Redis with RediSearch module (RedisStack or Redis Cloud)

### Running Redis with Docker

```bash
docker-compose up -d
```

## Examples

See the `examples/` directory for more:

- `basic_usage.py` - Basic cache operations, multi-tenancy, reranking
- `langchain_example.py` - LangChain integration with streaming
- `google_adk_example.py` - Google ADK integration with multi-user sessions
- `l1_l2_cache_example.py` - L1/L2 cache hierarchy demonstration
- `context_aware_example.py` - Context-aware caching with isolation
- `tag_invalidation_example.py` - Tag-based cache invalidation
- `observability_example.py` - Metrics, monitoring, and distributed tracing
- `batch_operations_example.py` - Batch check performance comparison
- `staleness_example.py` - Cache staleness mitigation strategies
- `stale_refresh_callback_example.py` - Automatic background refresh with callbacks

## Architecture

```
src/semantic_cache/
├── core/
│   ├── cache_manager.py    # Async cache manager
│   ├── config.py           # Configuration with Pydantic
│   ├── metrics.py          # Metrics tracking
│   ├── l1_cache.py         # In-memory L1 cache
│   └── tag_manager.py      # Tag-based invalidation
├── vectorizers/
│   └── factory.py          # Vectorizer factory
├── rerankers/
│   └── factory.py          # Reranker factory
├── integrations/
│   ├── langchain.py        # LangChain integration
│   └── google_adk.py       # Google ADK integration
└── utils/
    ├── logging.py          # Structured logging
    └── exceptions.py       # Custom exceptions
```

## Performance

- **L1 Cache** - In-memory cache with <1ms latency (optional)
- **L2 Cache** - Redis vector store with ~20ms latency
- **Async/Await** - Non-blocking operations for high throughput
- **Connection Pooling** - Efficient Redis connection management
- **Retry Logic** - Exponential backoff for resilience
- **Graceful Degradation** - Returns None on cache errors instead of crashing

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

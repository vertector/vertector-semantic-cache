# Vertector Semantic Cache

Enterprise-grade async semantic caching for AI agents using RedisVL.

## Features

- 🚀 **Semantic Similarity** - Cache responses based on meaning, not exact matches
- ⚡ **L1/L2 Cache Hierarchy** - In-memory (L1) + Redis (L2) for 10-1000x performance
- 🎯 **Context-Aware Caching** - Isolate cache by user, conversation, or custom context
- 🏷️ **Tag-Based Invalidation** - Efficiently invalidate related entries
- 📦 **Batch Operations** - Check/store multiple prompts efficiently
- 🔄 **Staleness Mitigation** - Version-based invalidation and stale-while-revalidate
- 📊 **Observability** - L1/L2 metrics, OpenTelemetry tracing, Prometheus export
- 🔌 **Easy Integration** - Async wrappers for LangChain and Google ADK
- 🛡️ **Type Safe** - Full type hints with Pydantic validation

## Installation

```bash
# Basic installation
pip install vertector-semantic-cache

# With LangChain support
pip install vertector-semantic-cache[langchain]

# With Google ADK support
pip install vertector-semantic-cache[google-adk]

# With observability (OpenTelemetry tracing)
pip install vertector-semantic-cache[observability]

# With all optional dependencies
pip install vertector-semantic-cache[all]
```

## Quick Start

### Prerequisites

1. **Python >= 3.10**
2. **Redis 8+** (has built-in vector search) or Redis Cloud

```bash
# Start Redis with Docker
docker-compose up -d
```

### Basic Usage

```python
import asyncio
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig

async def main():
    # Configure cache
    config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="my_cache",
        ttl=3600,  # 1 hour
        distance_threshold=0.2,  # Semantic similarity threshold
        overwrite=True,  # Overwrite existing index
    )
    
    # Use cache with context manager
    async with AsyncSemanticCacheManager(config) as cache:
        # Store a response
        await cache.store(
            prompt="What is the capital of Ghana?",
            response="The capital of Ghana is Accra."
        )
        
        # Check for exact match
        result = await cache.check("What is the capital of Ghana?")
        print(result)  # "The capital of Ghana is Accra."
        
        # Check for semantic match (different wording, same meaning)
        result = await cache.check("Tell me the capital city of Ghana")
        print(result)  # "The capital of Ghana is Accra."

asyncio.run(main())
```

### LangChain Integration

```python
import asyncio
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig
from vertector_semantic_cache.integrations import AsyncLangChainCachedLLM

load_dotenv()

async def main():
    # Setup cache
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="langchain_cache",
        overwrite=True,
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Setup LLM with caching
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )
    cached_llm = AsyncLangChainCachedLLM(cache_manager, llm)
    
    async with cache_manager:
        # First call - calls LLM
        response1 = await cached_llm.query(
            prompt="What is the capital of Ghana?",
            system_message="You are a helpful assistant."
        )
        
        # Second call - returns from cache (instant!)
        response2 = await cached_llm.query(
            prompt="Tell me the capital city of Ghana",  # Semantically similar
            system_message="You are a helpful assistant."
        )

asyncio.run(main())
```

### Google ADK Integration

```python
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps.app import App
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig
from vertector_semantic_cache.integrations import AsyncGoogleADKCachedAgent

load_dotenv()

async def main():
    # Setup cache
    cache_config = CacheConfig(
        redis_url="redis://localhost:6380",
        name="adk_cache",
        overwrite=True,
    )
    cache_manager = AsyncSemanticCacheManager(cache_config)
    
    # Setup agent
    agent = Agent(
        name="my_agent",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant."
    )
    app = App(name="my_app", root_agent=agent)
    
    # Create cached agent
    cached_agent = AsyncGoogleADKCachedAgent(cache_manager, agent, app)
    
    async with cache_manager:
        response = await cached_agent.query("What is the capital of Ghana?")
        print(response)
        
        await cached_agent.close()

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
GOOGLE_API_KEY=your-api-key
```

### Vectorizer Configuration

```python
from vertector_semantic_cache import CacheConfig, VectorizerConfig

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
from vertector_semantic_cache import CacheConfig, RerankerConfig

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
from vertector_semantic_cache import CacheConfig
from vertector_semantic_cache.core.config import L1CacheConfig

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

Check or store multiple prompts efficiently:

```python
# Batch check multiple prompts
prompts = ["What is AI?", "What is ML?", "What is DL?"]
results = await cache.batch_check(prompts)
# Returns: [response1, response2, None]  # One cache miss
```

### Cache Staleness Mitigation

Prevent serving outdated data with automatic staleness detection:

```python
config = CacheConfig(
    ttl=3600,  # 1 hour TTL
    
    # Stale-while-revalidate
    enable_stale_while_revalidate=True,
    stale_tolerance_seconds=300,       # Serve stale up to 5min old
    max_stale_age_seconds=3600,        # Refuse if older than 1hr
    
    # Version-based invalidation
    enable_version_checking=True,
    cache_version="v1.0.0",  # Bump to invalidate all entries
)
```

## Examples

See the `examples/` directory for working code:

| Example | Description |
|---------|-------------|
| `basic_usage.py` | Basic cache operations |
| `langchain_example.py` | LangChain integration |
| `google_adk_example.py` | Google ADK integration |
| `l1_l2_cache_example.py` | L1/L2 cache hierarchy |
| `context_aware_example.py` | Context-aware caching |
| `tag_invalidation_example.py` | Tag-based invalidation |
| `batch_operations_example.py` | Batch operations |
| `staleness_example.py` | Staleness mitigation |
| `observability_example.py` | Monitoring & observability |

Run an example:
```bash
PYTHONPATH=src python examples/basic_usage.py
```

## Architecture

```
src/vertector_semantic_cache/
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
- **Graceful Degradation** - Returns None on cache errors

## Documentation

- [Advanced Caching Guide](docs/ADVANCED_CACHING.md) - L1/L2, context-aware, tags
- [Observability Guide](docs/OBSERVABILITY.md) - Metrics, tracing, monitoring
- [Documentation Index](docs/INDEX.md) - Full documentation index

## Requirements

- Python >= 3.10
- Redis 8+ (has built-in vector search) or Redis Cloud

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

**GitHub**: [github.com/vertector/vertector-semantic-cache](https://github.com/vertector/vertector-semantic-cache)

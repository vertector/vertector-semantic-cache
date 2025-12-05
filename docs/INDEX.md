# Vertector Semantic Cache - Documentation Index

Welcome to the vertector-semantic-cache documentation! This index will help you find the information you need.

## Quick Links

- [Getting Started](#getting-started)
- [Core Features](#core-features)
- [Advanced Features](#advanced-features)
- [Operations](#operations)

---

## Getting Started

### Installation & Setup
- **[README.md](../README.md)** - Installation, quick start, and basic usage
- **[Examples](../examples/)** - Working code examples for all features

### First Steps
1. Install: `pip install vertector-semantic-cache`
2. Start Redis: `docker-compose up -d`
3. Run basic example: `PYTHONPATH=src python examples/basic_usage.py`

---

## Core Features

### Basic Caching
- **Semantic Similarity**: Cache responses based on meaning, not exact matches
- **Multi-Tenancy**: User isolation with filterable fields
- **Async Support**: Built with `async/await` for non-blocking operations
- **Type Safety**: Full type hints with Pydantic validation

**Documentation**: [README.md](../README.md#quick-start)  
**Examples**: `examples/basic_usage.py`

---

## Advanced Features

### L1/L2 Cache Hierarchy
Two-tier caching for optimal performance: in-memory L1 (<1ms) + Redis L2 (~20ms).

**Documentation**: [ADVANCED_CACHING.md](ADVANCED_CACHING.md#l1l2-cache-hierarchy)  
**Examples**: `examples/l1_l2_cache_example.py`  
**Key Benefits**:
- 100-1000x faster lookups with L1
- Automatic L1 population from L2
- Configurable eviction strategies (LRU, LFU, TTL)

### Context-Aware Caching
Isolate cache entries by context (user persona, conversation, session).

**Documentation**: [ADVANCED_CACHING.md](ADVANCED_CACHING.md#context-aware-caching)  
**Examples**: `examples/context_aware_example.py`  
**Use Cases**:
- Multi-user applications
- Conversation-specific responses
- Role-based caching

### Tag-Based Invalidation
Flexible cache management with custom tags.

**Documentation**: [ADVANCED_CACHING.md](ADVANCED_CACHING.md#tag-based-invalidation)  
**Examples**: `examples/tag_invalidation_example.py`  
**Features**:
- Tag entries with multiple tags
- Invalidate by single tag or multiple tags
- Support for OR/AND logic

### Observability & Monitoring
Production-grade metrics and tracing.

**Documentation**: [OBSERVABILITY.md](OBSERVABILITY.md)  
**Examples**: `examples/observability_example.py`  
**Features**:
- L1/L2 metrics breakdown
- Context and tag distribution tracking
- Prometheus export
- Optional OpenTelemetry tracing

---

## Operations

### Monitoring & Alerting
- **Metrics**: [OBSERVABILITY.md](OBSERVABILITY.md#enhanced-metrics)
- **Prometheus**: [OBSERVABILITY.md](OBSERVABILITY.md#prometheus-integration)
- **Grafana**: [OBSERVABILITY.md](OBSERVABILITY.md#grafana-dashboards)
- **Alerts**: [OBSERVABILITY.md](OBSERVABILITY.md#alerting)

### Performance Tuning
- **Best Practices**: [ADVANCED_CACHING.md](ADVANCED_CACHING.md#performance-best-practices)
- **L1 Cache Sizing**: Balance memory vs hit rate
- **Context Fields**: Optimize for your use case
- **Tag Strategy**: Hierarchical naming conventions

---

## Feature Comparison

| Feature | Default | Requires Config | Requires Install |
|---------|---------|----------------|------------------|
| **Basic Caching** | ✅ | No | No |
| **L1 Cache** | ❌ | Yes | No |
| **L2 Cache** | ✅ | No | No |
| **Context-Aware** | ✅ | No | No |
| **Tag-Based Invalidation** | ✅ | No | No |
| **Enhanced Metrics** | ✅ | No | No |
| **Distributed Tracing** | ❌ | Yes | Yes (`[observability]`) |

---

## Quick Reference

### Common Tasks

**Enable L1 Cache:**
```python
l1_cache=L1CacheConfig(enabled=True, max_size=1000)
```

**Use Context:**
```python
await cache.check(prompt, context={"persona": "developer"})
```

**Tag Entries:**
```python
await cache.store(prompt, response, tags=["category:ai"])
```

**Enable Tracing:**
```python
observability=ObservabilityConfig(enable_tracing=True)
```

---

## Support & Contributing

**GitHub**: [github.com/vertector/vertector-semantic-cache](https://github.com/vertector/vertector-semantic-cache)

---

## Documentation Updates

This documentation is current as of **December 5, 2024**.

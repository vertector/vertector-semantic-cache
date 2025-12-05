# Observability & Monitoring Guide

Complete guide to monitoring and observing your semantic cache in production.

## Table of Contents

- [Overview](#overview)
- [Enhanced Metrics](#enhanced-metrics)
- [Distributed Tracing](#distributed-tracing)
- [Prometheus Integration](#prometheus-integration)
- [Grafana Dashboards](#grafana-dashboards)
- [Alerting](#alerting)
- [Production Best Practices](#production-best-practices)

---

## Overview

The semantic cache provides comprehensive observability out-of-the-box:

| Feature | Enabled by Default | Requires Installation |
|---------|-------------------|----------------------|
| **Enhanced Metrics** | ✅ Yes | No |
| **L1/L2 Breakdown** | ✅ Yes | No |
| **Context Tracking** | ✅ Yes | No |
| **Tag Metrics** | ✅ Yes | No |
| **Prometheus Export** | ✅ Yes | No |
| **Distributed Tracing** | ❌ No (opt-in) | Yes (`[observability]`) |

---

## Enhanced Metrics

### Quick Start

```python
from vertector_semantic_cache import AsyncSemanticCacheManager, CacheConfig

async with AsyncSemanticCacheManager(config) as cache:
    # Use cache normally...
    await cache.store(prompt, response)
    result = await cache.check(prompt)
    
    # Get detailed metrics
    metrics = cache.get_metrics()
    print(f"Hit rate: {metrics['hit_rate_percentage']}%")
```

### Metrics Structure

```python
{
    # Overall cache metrics
    "total_queries": 1000,
    "cache_hits": 850,
    "cache_misses": 150,
    "hit_rate_percentage": 85.0,
    "llm_calls_avoided": 850,
    "errors": 0,
    "error_rate_percentage": 0.0,
    
    # L1 cache breakdown
    "l1_cache": {
        "hits": 680,
        "misses": 170,
        "hit_rate_percentage": 80.0,
        "avg_latency_ms": 0.025
    },
    
    # L2 cache breakdown
    "l2_cache": {
        "hits": 170,
        "misses": 150,
        "hit_rate_percentage": 53.1,
        "avg_latency_ms": 18.5
    },
    
    # Context distribution
    "context_hits": {
        "developer": 450,
        "manager": 280,
        "analyst": 120
    },
    
    # Tag invalidations
    "tag_invalidations": {
        "product:iphone": 15,
        "category:electronics": 42
    },
    
    "timestamp": "2024-12-01T14:00:00Z"
}
```

### Interpreting Metrics

#### Overall Hit Rate
```python
hit_rate = metrics['hit_rate_percentage']

# Guidelines:
# > 80%: Excellent - cache is very effective
# 60-80%: Good - typical for production
# 40-60%: Fair - consider tuning
# < 40%: Poor - investigate issues
```

#### L1 vs L2 Performance

```python
l1_hits = metrics['l1_cache']['hits']
l2_hits = metrics['l2_cache']['hits']
total_hits = l1_hits + l2_hits

l1_percentage = (l1_hits / total_hits * 100) if total_hits > 0 else 0

# Guidelines:
# > 75% L1 hits: Excellent - hot data in memory
# 50-75% L1 hits: Good - balanced usage
# < 50% L1 hits: Consider increasing L1 size
```

#### Latency Analysis

```python
l1_latency = metrics['l1_cache']['avg_latency_ms']
l2_latency = metrics['l2_cache']['avg_latency_ms']

# Expected ranges:
# L1: 0.01-0.1ms (ideal)
# L2: 10-30ms (typical)
# 
# If L2 > 50ms: Check Redis performance
```

---

## Distributed Tracing

### Installation

```bash
pip install vertector-semantic-cache[observability]
```

This installs:
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp`
- `opentelemetry-exporter-jaeger`

### Configuration

```python
from vertector_semantic_cache.core.config import ObservabilityConfig

config = CacheConfig(
    redis_url="redis://localhost:6380",
    observability=ObservabilityConfig(
        enable_tracing=True,
        tracing_exporter="jaeger",
        tracing_endpoint="http://localhost:14268",
        service_name="my-app-cache"
    )
)
```

> [!TIP]
> For console tracing in development, spans are exported immediately. For production (otlp/jaeger), call `shutdown_tracing()` to flush pending spans on exit, or the atexit handler will do it automatically.

### Exporters

#### 1. Console (Development)

```python
observability=ObservabilityConfig(
    enable_tracing=True,
    tracing_exporter="console"
)
```

**Output:**
```json
{
  "name": "cache.check",
  "context": {...},
  "kind": "SpanKind.INTERNAL",
  "parent_id": null,
  "start_time": "2024-12-01T14:00:00.000000Z",
  "end_time": "2024-12-01T14:00:00.025000Z",
  "status": {"status_code": "OK"},
  "attributes": {
    "cache.prompt_length": 25,
    "cache.user_id": "user_123",
    "cache_hit": true,
    "cache_layer": "L1",
    "latency_ms": 0.052
  }
}
```

#### 2. Jaeger (Production)

**Setup Jaeger:**
```bash
docker run -d --name jaeger \
  -p 14268:14268 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

**Configure:**
```python
observability=ObservabilityConfig(
    enable_tracing=True,
    tracing_exporter="jaeger",
    tracing_endpoint="http://localhost:14268"
)
```

**Access UI:** http://localhost:16686

#### 3. OTLP (OpenTelemetry Collector)

```python
observability=ObservabilityConfig(
    enable_tracing=True,
    tracing_exporter="otlp",
    tracing_endpoint="http://localhost:4317"
)
```

### Span Attributes

Each cache operation creates spans with rich attributes:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `cache.prompt_length` | Length of the prompt | `42` |
| `cache.user_id` | User identifier | `"user_123"` |
| `cache.has_context` | Whether context provided | `true` |
| `cache_hit` | Hit or miss | `true` |
| `cache_layer` | Which cache layer (L1/L2) | `"L1"` |
| `latency_ms` | Total operation latency | `0.52` |
| `l1_latency_ms` | L1 operation latency | `0.05` |
| `l2_latency_ms` | L2 operation latency | `15.2` |
| `error` | Error occurred | `false` |
| `error_message` | Error details | `"Connection timeout"` |

### Analyzing Traces

#### Finding Slow Operations

In Jaeger:
1. Search for service: `my-app-cache`
2. Filter by operation: `cache.check`
3. Sort by duration (descending)
4. Investigate spans > 50ms

#### Identifying L1 vs L2 Performance

```
Trace: 125ms total
  └─ cache.check (125ms)
     ├─ L1 Miss (0.05ms)
     └─ L2 Hit (124.95ms)  ← Investigate Redis performance
```

---

## Prometheus Integration

### Exposing Metrics

```python
from fastapi import FastAPI
from vertector_semantic_cache import AsyncSemanticCacheManager

app = FastAPI()
cache_manager = AsyncSemanticCacheManager(config)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    prometheus_metrics = cache_manager.get_metrics_prometheus()
    return Response(
        content=prometheus_metrics,
        media_type="text/plain"
    )
```

### Available Metrics

#### Counters

```promql
# Total queries
semantic_cache_queries_total

# Cache hits/misses
semantic_cache_hits_total
semantic_cache_misses_total

# L1 cache
semantic_cache_l1_hits_total
semantic_cache_l1_misses_total

# L2 cache
semantic_cache_l2_hits_total
semantic_cache_l2_misses_total

# LLM calls avoided
semantic_cache_llm_calls_avoided

# Errors
semantic_cache_errors_total

# Context hits (with labels)
semantic_cache_context_hits_total{context_type="developer"}

# Tag invalidations (with labels)
semantic_cache_tag_invalidations_total{tag="product:iphone"}
```

#### Gauges

```promql
# Hit rates
semantic_cache_hit_rate
semantic_cache_l1_hit_rate
semantic_cache_l2_hit_rate

# Latencies
semantic_cache_l1_latency_ms
semantic_cache_l2_latency_ms
```

### Prometheus Configuration

`prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'semantic-cache'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

## Grafana Dashboards

### Example Dashboard Panels

#### 1. Overall Hit Rate

```promql
# Query
rate(semantic_cache_hits_total[5m]) / 
rate(semantic_cache_queries_total[5m]) * 100

# Panel Type: Time Series
# Unit: Percent (0-100)
# Threshold: Yellow < 60%, Red < 40%
```

#### 2. L1 vs L2 Hit Distribution

```promql
# L1 Hits
rate(semantic_cache_l1_hits_total[5m])

# L2 Hits
rate(semantic_cache_l2_hits_total[5m])

# Panel Type: Stacked Area Chart
# Legend: L1 Hits, L2 Hits
```

#### 3. Latency Comparison

```promql
# L1 Latency
semantic_cache_l1_latency_ms

# L2 Latency
semantic_cache_l2_latency_ms

# Panel Type: Time Series
# Unit: milliseconds
# Y-axis: Logarithmic scale
```

#### 4. Context Distribution

```promql
# Query
sum by (context_type) (semantic_cache_context_hits_total)

# Panel Type: Pie Chart
# Show: Top 10 contexts
```

#### 5. Cache Savings

```promql
# LLM Calls Avoided
rate(semantic_cache_llm_calls_avoided[5m]) * 3600

# Panel Type: Stat
# Unit: Calls per hour
# Color: Green
```

#### 6. Error Rate

```promql
# Query
rate(semantic_cache_errors_total[5m]) / 
rate(semantic_cache_queries_total[5m]) * 100

# Panel Type: Time Series
# Unit: Percent
# Threshold: Yellow > 1%, Red > 5%
```

### Complete Dashboard JSON

See `monitoring/grafana-dashboard.json` for a pre-built dashboard template.

---

## Alerting

### Prometheus Alert Rules

`alert_rules.yml`:
```yaml
groups:
  - name: semantic_cache_alerts
    interval: 30s
    rules:
      # Low hit rate alert
      - alert: LowCacheHitRate
        expr: |
          (rate(semantic_cache_hits_total[5m]) / 
           rate(semantic_cache_queries_total[5m]) * 100) < 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate below 50%"
          description: "Hit rate: {{ $value }}%"
      
      # High error rate
      - alert: HighCacheErrorRate
        expr: |
          (rate(semantic_cache_errors_total[5m]) / 
           rate(semantic_cache_queries_total[5m]) * 100) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Cache error rate above 5%"
      
      # High L2 latency
      - alert: HighL2Latency
        expr: semantic_cache_l2_latency_ms > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "L2 cache latency is high"
          description: "L2 latency: {{ $value }}ms"
      
      # L1 cache not being used
      - alert: L1CacheUnused
        expr: |
          rate(semantic_cache_l1_hits_total[5m]) == 0 AND
          rate(semantic_cache_queries_total[5m]) > 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "L1 cache receiving no hits"
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| **Overall Hit Rate** | < 60% | < 40% |
| **L1 Hit Rate** | < 70% | < 50% |
| **Error Rate** | > 1% | > 5% |
| **L2 Latency** | > 50ms | > 100ms |
| **L1 Latency** | > 1ms | > 5ms |

---

## Production Best Practices

### 1. Baseline Your Metrics

```python
# Run for 24 hours in production
# Record baseline metrics:
baseline = {
    "hit_rate": 75.0,
    "l1_hit_rate": 82.0,
    "l2_latency": 22.5,
    "error_rate": 0.1
}

# Set alerts based on significant deviation
# e.g., hit_rate < baseline * 0.8
```

### 2. Monitor Trends

```promql
# Week-over-week comparison
(
  rate(semantic_cache_hits_total[1h]) -
  rate(semantic_cache_hits_total[1h] offset 1w)
) / rate(semantic_cache_hits_total[1h] offset 1w) * 100
```

### 3. Correlate with Application Metrics

```python
# Track cache performance alongside:
- Response times
- API request rates
- LLM API costs
- User satisfaction scores
```

### 4. Regular Reviews

Weekly:
- Review hit rate trends
- Check error logs
- Analyze context distribution

Monthly:
- Capacity planning (L1 size, Redis memory)
- Cost savings analysis
- Performance optimization opportunities

### 5. Incident Response

When alerts fire:

1. **Low Hit Rate**:
   - Check for recent config changes
   - Verify L1 cache is enabled
   - Review query patterns (new use cases?)

2. **High Errors**:
   - Check Redis connectivity
   - Review application logs
   - Verify Redis memory usage

3. **High Latency**:
   - Check Redis performance
   - Monitor network latency
   - Review L1 cache size

---

## Example: Complete Monitoring Stack

### Docker Compose Setup

```yaml
version: '3.8'

services:
  # Your app
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - JAEGER_ENDPOINT=http://jaeger:14268
  
  # Redis
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
  
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml
  
  # Grafana
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./monitoring/grafana-dashboard.json:/etc/grafana/provisioning/dashboards/semantic-cache.json
  
  # Jaeger
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "14268:14268"  # Collector
      - "16686:16686"  # UI
```

### Access Points

- **Application**: http://localhost:8000
- **Metrics**: http://localhost:8000/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Jaeger**: http://localhost:16686

---

## Troubleshooting

### Metrics Not Updating

**Problem**: Metrics stay at 0

**Solutions**:
1. Ensure you're using the cache (`check()`, `store()`)
2. Verify metrics are enabled (default: yes)
3. Check for initialization errors

### Tracing Not Working

**Problem**: No spans in Jaeger

**Solutions**:
1. Verify OpenTelemetry is installed
2. Check tracer configuration
3. Ensure Jaeger is accessible
4. Look for warnings in logs

### High Memory Usage

**Problem**: L1 cache consuming too much memory

**Solutions**:
```python
# Reduce L1 cache size
l1_cache=L1CacheConfig(
    enabled=True,
    max_size=500  # Reduce from 1000
)

# Or use more aggressive eviction
l1_cache=L1CacheConfig(
    ttl_seconds=60,  # Shorter TTL
    eviction_strategy="ttl"
)
```

---

## See Also

- [ADVANCED_CACHING.md](ADVANCED_CACHING.md) - Feature documentation
- [README.md](../README.md) - Getting started
- [Examples](../examples/observability_example.py) - Working example

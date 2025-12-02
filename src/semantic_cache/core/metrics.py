"""Cache performance metrics tracking."""

from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime, timezone
import threading
from collections import defaultdict


@dataclass
class CacheMetrics:
    """Thread-safe metrics tracking for cache performance."""
    
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_latency_saved: float = 0.0
    llm_calls_avoided: int = 0
    errors: int = 0
    rerank_operations: int = 0
    
    # L1/L2 breakdown
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    
    # Context and tag metrics
    context_hits: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tag_invalidations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Latency tracking
    l1_latencies: List[float] = field(default_factory=list)
    l2_latencies: List[float] = field(default_factory=list)
    
    # Lock for thread-safe operations
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    
    def increment_query(self) -> None:
        """Increment total query count."""
        with self._lock:
            self.total_queries += 1
    
    def record_hit(self, latency_saved: float = 0.0) -> None:
        """Record a cache hit."""
        with self._lock:
            self.cache_hits += 1
            self.llm_calls_avoided += 1
            self.total_latency_saved += latency_saved
    
    def record_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.cache_misses += 1
    
    def record_error(self) -> None:
        """Record an error."""
        with self._lock:
            self.errors += 1
    
    def record_rerank(self) -> None:
        """Record a rerank operation."""
        with self._lock:
            self.rerank_operations += 1
    
    def record_l1_hit(self, latency: float = 0.0) -> None:
        """Record an L1 cache hit."""
        with self._lock:
            self.l1_hits += 1
            if latency > 0:
                self.l1_latencies.append(latency)
                # Keep only last 1000 latencies to avoid memory bloat
                if len(self.l1_latencies) > 1000:
                    self.l1_latencies = self.l1_latencies[-1000:]
    
    def record_l1_miss(self) -> None:
        """Record an L1 cache miss."""
        with self._lock:
            self.l1_misses += 1
    
    def record_l2_hit(self, latency: float = 0.0) -> None:
        """Record an L2 cache hit."""
        with self._lock:
            self.l2_hits += 1
            if latency > 0:
                self.l2_latencies.append(latency)
                if len(self.l2_latencies) > 1000:
                    self.l2_latencies = self.l2_latencies[-1000:]
    
    def record_l2_miss(self) -> None:
        """Record an L2 cache miss."""
        with self._lock:
            self.l2_misses += 1
    
    def record_context_hit(self, context_type: str) -> None:
        """Record a cache hit for a specific context type."""
        with self._lock:
            self.context_hits[context_type] += 1
    
    def record_tag_invalidation(self, tag: str, count: int = 1) -> None:
        """Record a tag invalidation."""
        with self._lock:
            self.tag_invalidations[tag] += count
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        with self._lock:
            if self.total_queries == 0:
                return 0.0
            return (self.cache_hits / self.total_queries) * 100
    
    @property
    def cost_savings_percentage(self) -> float:
        """Calculate cost savings percentage."""
        with self._lock:
            if self.total_queries == 0:
                return 0.0
            return (self.llm_calls_avoided / self.total_queries) * 100
    
    @property
    def average_latency_saved(self) -> float:
        """Calculate average latency saved per cache hit (in milliseconds)."""
        with self._lock:
            if self.cache_hits == 0:
                return 0.0
            return (self.total_latency_saved / self.cache_hits) * 1000
    
    @property
    def stale_served_count(self) -> int:
        """Number of stale entries served."""
        with self._lock:
            return self._stale_served_count
    
    @property
    def stale_refused_count(self) -> int:
        """Number of stale entries refused (too old)."""
        with self._lock:
            return self._stale_refused_count
    
    @property
    def version_mismatches(self) -> int:
        """Number of version mismatches detected."""
        with self._lock:
            return self._version_mismatches
    
    @property
    def average_stale_age_seconds(self) -> float:
        """Average age of stale entries served."""
        with self._lock:
            if self._stale_served_count == 0:
                return 0.0
            return self._total_age_seconds / self._stale_served_count
    
    def record_stale_served(self, age_seconds: float):
        """Record that a stale entry was served."""
        with self._lock:
            self._stale_served_count += 1
            self._total_age_seconds += age_seconds
    
    def record_stale_refused(self):
        """Record that a stale entry was refused."""
        with self._lock:
            self._stale_refused_count += 1
    
    def record_version_mismatch(self):
        """Record a version mismatch."""
        with self._lock:
            self._version_mismatches += 1
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        with self._lock:
            if self.total_queries == 0:
                return 0.0
            return (self.errors / self.total_queries) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        with self._lock:
            # Calculate metrics directly to avoid deadlock with properties
            hit_rate = (self.cache_hits / self.total_queries * 100) if self.total_queries > 0 else 0.0
            cost_savings = (self.llm_calls_avoided / self.total_queries * 100) if self.total_queries > 0 else 0.0
            avg_latency = (self.total_latency_saved / self.cache_hits * 1000) if self.cache_hits > 0 else 0.0
            error_rate = (self.errors / self.total_queries * 100) if self.total_queries > 0 else 0.0
            
            return {
                "total_queries": self.total_queries,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate_percentage": round(hit_rate, 2),
                "cost_savings_percentage": round(cost_savings, 2),
                "llm_calls_avoided": self.llm_calls_avoided,
                "avg_latency_saved_ms": round(avg_latency, 2),
                "errors": self.errors,
                "error_rate_percentage": round(error_rate, 2),
                "rerank_operations": self.rerank_operations,
                "l1_cache": {
                    "hits": self.l1_hits,
                    "misses": self.l1_misses,
                    "hit_rate_percentage": round((self.l1_hits / (self.l1_hits + self.l1_misses) * 100) if (self.l1_hits + self.l1_misses) > 0 else 0.0, 2),
                    "avg_latency_ms": round(sum(self.l1_latencies) / len(self.l1_latencies) * 1000, 3) if self.l1_latencies else 0.0,
                },
                "l2_cache": {
                    "hits": self.l2_hits,
                    "misses": self.l2_misses,
                    "hit_rate_percentage": round((self.l2_hits / (self.l2_hits + self.l2_misses) * 100) if (self.l2_hits + self.l2_misses) > 0 else 0.0, 2),
                    "avg_latency_ms": round(sum(self.l2_latencies) / len(self.l2_latencies) * 1000, 3) if self.l2_latencies else 0.0,
                },
                "context_hits": dict(self.context_hits),
                "tag_invalidations": dict(self.tag_invalidations),
                "staleness": {
                    "stale_served_count": self.stale_served_count,
                    "stale_refused_count": self.stale_refused_count,
                    "version_mismatches": self.version_mismatches,
                    "average_stale_age_seconds": round(self.average_stale_age_seconds, 2),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format with L1/L2 breakdown."""
        with self._lock:
            hit_rate = (self.cache_hits / self.total_queries * 100) if self.total_queries > 0 else 0.0
            l1_hit_rate = (self.l1_hits / (self.l1_hits + self.l1_misses) * 100) if (self.l1_hits + self.l1_misses) > 0 else 0.0
            l2_hit_rate = (self.l2_hits / (self.l2_hits + self.l2_misses) * 100) if (self.l2_hits + self.l2_misses) > 0 else 0.0
            l1_avg_latency = (sum(self.l1_latencies) / len(self.l1_latencies) * 1000) if self.l1_latencies else 0.0
            l2_avg_latency = (sum(self.l2_latencies) / len(self.l2_latencies) * 1000) if self.l2_latencies else 0.0
            
            metrics = [
                # Overall metrics
                f"# HELP semantic_cache_queries_total Total number of cache queries",
                f"# TYPE semantic_cache_queries_total counter",
                f"semantic_cache_queries_total {self.total_queries}",
                "",
                f"# HELP semantic_cache_hits_total Total number of cache hits",
                f"# TYPE semantic_cache_hits_total counter",
                f"semantic_cache_hits_total {self.cache_hits}",
                "",
                f"# HELP semantic_cache_misses_total Total number of cache misses",
                f"# TYPE semantic_cache_misses_total counter",
                f"semantic_cache_misses_total {self.cache_misses}",
                "",
                f"# HELP semantic_cache_hit_rate Cache hit rate percentage",
                f"# TYPE semantic_cache_hit_rate gauge",
                f"semantic_cache_hit_rate {hit_rate}",
                "",
                
                # L1 metrics
                f"# HELP semantic_cache_l1_hits_total Total L1 cache hits",
                f"# TYPE semantic_cache_l1_hits_total counter",
                f"semantic_cache_l1_hits_total {self.l1_hits}",
                "",
                f"# HELP semantic_cache_l1_misses_total Total L1 cache misses",
                f"# TYPE semantic_cache_l1_misses_total counter",
                f"semantic_cache_l1_misses_total {self.l1_misses}",
                "",
                f"# HELP semantic_cache_l1_hit_rate L1 cache hit rate percentage",
                f"# TYPE semantic_cache_l1_hit_rate gauge",
                f"semantic_cache_l1_hit_rate {l1_hit_rate}",
                "",
                f"# HELP semantic_cache_l1_latency_ms Average L1 latency in milliseconds",
                f"# TYPE semantic_cache_l1_latency_ms gauge",
                f"semantic_cache_l1_latency_ms {l1_avg_latency}",
                "",
                
                # L2 metrics
                f"# HELP semantic_cache_l2_hits_total Total L2 cache hits",
                f"# TYPE semantic_cache_l2_hits_total counter",
                f"semantic_cache_l2_hits_total {self.l2_hits}",
                "",
                f"# HELP semantic_cache_l2_misses_total Total L2 cache misses",
                f"# TYPE semantic_cache_l2_misses_total counter",
                f"semantic_cache_l2_misses_total {self.l2_misses}",
                "",
                f"# HELP semantic_cache_l2_hit_rate L2 cache hit rate percentage",
                f"# TYPE semantic_cache_l2_hit_rate gauge",
                f"semantic_cache_l2_hit_rate {l2_hit_rate}",
                "",
                f"# HELP semantic_cache_l2_latency_ms Average L2 latency in milliseconds",
                f"# TYPE semantic_cache_l2_latency_ms gauge",
                f"semantic_cache_l2_latency_ms {l2_avg_latency}",
                "",
                
                # Other metrics
                f"# HELP semantic_cache_llm_calls_avoided Total LLM calls avoided",
                f"# TYPE semantic_cache_llm_calls_avoided counter",
                f"semantic_cache_llm_calls_avoided {self.llm_calls_avoided}",
                "",
                f"# HELP semantic_cache_errors_total Total number of errors",
                f"# TYPE semantic_cache_errors_total counter",
                f"semantic_cache_errors_total {self.errors}",
                "",
                f"# HELP semantic_cache_rerank_operations_total Total rerank operations",
                f"# TYPE semantic_cache_rerank_operations_total counter",
                f"semantic_cache_rerank_operations_total {self.rerank_operations}",
                "",
            ]
            
            # Add context metrics
            if self.context_hits:
                metrics.extend([
                    f"# HELP semantic_cache_context_hits_total Cache hits by context type",
                    f"# TYPE semantic_cache_context_hits_total counter",
                ])
                for context_type, count in self.context_hits.items():
                    metrics.append(f'semantic_cache_context_hits_total{{context_type="{context_type}"}} {count}')
                metrics.append("")
            
            # Add tag metrics
            if self.tag_invalidations:
                metrics.extend([
                    f"# HELP semantic_cache_tag_invalidations_total Tag invalidations",
                    f"# TYPE semantic_cache_tag_invalidations_total counter",
                ])
                for tag, count in self.tag_invalidations.items():
                    metrics.append(f'semantic_cache_tag_invalidations_total{{tag="{tag}"}} {count}')
                metrics.append("")
            
            return "\n".join(metrics)

    

    
    def reset(self) -> None:
        """Reset all metrics to zero."""
        with self._lock:
            self.total_queries = 0
            self.cache_hits = 0
            self.cache_misses = 0
            self.total_latency_saved = 0.0
            self.llm_calls_avoided = 0
            self.errors = 0
            self.rerank_operations = 0

"""
Enterprise-Grade Async Semantic Cache Package

A production-ready semantic caching system for AI agents using RedisVL with:
- Full async/await support
- Reranker integration for improved relevance
- Multiple vectorizer support
- Type-safe with Pydantic validation
- Enterprise features: metrics, logging, retry logic
"""

__version__ = "0.1.0"
__author__ = "Vertector"

from semantic_cache.core.cache_manager import AsyncSemanticCacheManager
from semantic_cache.core.config import CacheConfig, VectorizerConfig, RerankerConfig
from semantic_cache.core.metrics import CacheMetrics
from semantic_cache.vectorizers.factory import VectorizerFactory
from semantic_cache.rerankers.factory import RerankerFactory
from semantic_cache.utils.exceptions import (
    SemanticCacheError,
    CacheConnectionError,
    VectorizerError,
    RerankerError,
    ConfigurationError,
)

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Core
    "AsyncSemanticCacheManager",
    "CacheConfig",
    "VectorizerConfig",
    "RerankerConfig",
    "CacheMetrics",
    # Factories
    "VectorizerFactory",
    "RerankerFactory",
    # Exceptions
    "SemanticCacheError",
    "CacheConnectionError",
    "VectorizerError",
    "RerankerError",
    "ConfigurationError",
]

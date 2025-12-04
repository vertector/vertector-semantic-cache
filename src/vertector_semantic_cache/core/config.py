"""Configuration classes for semantic cache using Pydantic."""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class L1CacheConfig(BaseModel):
    """Configuration for L1 in-memory cache."""
    
    enabled: bool = Field(default=False)
    max_size: int = Field(default=1000)
    ttl_seconds: int = Field(default=300)
    eviction_strategy: Literal["lru", "lfu", "ttl"] = Field(default="lru")


class ObservabilityConfig(BaseModel):
    """Configuration for observability and monitoring."""
    
    # Tracing
    enable_tracing: bool = Field(
        default=False,
        description="Enable OpenTelemetry distributed tracing"
    )
    tracing_exporter: Literal["console", "otlp", "jaeger"] = Field(
        default="console",
        description="Type of tracing exporter to use"
    )
    tracing_endpoint: Optional[str] = Field(
        default=None,
        description="Endpoint for tracing exporter (for otlp/jaeger)"
    )
    service_name: str = Field(
        default="semantic-cache",
        description="Service name for tracing"
    )
    
    # Metrics
    enable_detailed_metrics: bool = Field(
        default=True,
        description="Enable detailed metrics breakdown (L1/L2, context, tags)"
    )
    metrics_prefix: str = Field(
        default="semantic_cache",
        description="Prefix for Prometheus metrics"
    )
    
    # Logging
    enable_correlation_id: bool = Field(
        default=True,
        description="Enable correlation ID in logs"
    )
    log_performance: bool = Field(
        default=False,
        description="Log performance metrics for operations"
    )


class VectorizerConfig(BaseModel):
    """Configuration for embedding vectorizer."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    provider: Literal["huggingface", "openai", "cohere", "vertexai", "voyageai", "custom"] = Field(
        default="huggingface",
        description="Vectorizer provider"
    )
    model: str = Field(
        default="redis/langcache-embed-v1",
        description="Model name/path"
    )
    dtype: str = Field(
        default="float32",
        description="Data type for embeddings"
    )
    dims: Optional[int] = Field(
        default=None,
        description="Embedding dimensions (auto-detected if None)"
    )
    api_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="API configuration for cloud-based vectorizers"
    )
    
    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        valid_providers = ["huggingface", "openai", "cohere", "vertexai", "voyageai", "custom"]
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of {valid_providers}")
        return v


class RerankerConfig(BaseModel):
    """Configuration for result reranker."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    enabled: bool = Field(
        default=False,
        description="Whether to enable reranking"
    )
    provider: Literal["huggingface", "cohere", "voyageai"] = Field(
        default="huggingface",
        description="Reranker provider"
    )
    model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Reranker model name"
    )
    limit: int = Field(
        default=3,
        ge=1,
        description="Maximum number of results to return after reranking"
    )
    return_score: bool = Field(
        default=True,
        description="Whether to return reranking scores"
    )
    api_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="API configuration for cloud-based rerankers"
    )


class CacheConfig(BaseModel):
    """Configuration for semantic cache."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Redis connection
    redis_url: str = Field(
        default="redis://localhost:6380",
        description="Redis connection URL"
    )
    connection_kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional Redis connection arguments"
    )
    
    # Cache settings
    name: str = Field(
        default="semantic_cache",
        description="Cache name (used as Redis key prefix)"
    )
    ttl: Optional[int] = Field(
        default=3600,
        ge=0,
        description="Default TTL in seconds (None = no expiration)"
    )
    distance_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Semantic similarity threshold (0-1, lower = more strict)"
    )
    overwrite: bool = Field(
        default=False,
        description="Whether to overwrite existing index if schema doesn't match"
    )
    
    # Filterable fields for multi-tenancy
    filterable_fields: Optional[List[Dict[str, str]]] = Field(
        default_factory=lambda: [{"name": "user_id", "type": "tag"}],
        description="Fields that can be used for filtering"
    )
    
    # Vectorizer configuration
    vectorizer: VectorizerConfig = Field(
        default_factory=VectorizerConfig,
        description="Vectorizer configuration"
    )
    
    # Reranker configuration
    reranker: RerankerConfig = Field(
        default_factory=RerankerConfig,
        description="Reranker configuration"
    )
    
    # L1 Cache
    l1_cache: L1CacheConfig = Field(default_factory=L1CacheConfig)
    
    # Context-aware caching
    enable_context_hashing: bool = Field(default=True)
    context_fields: List[str] = Field(
        default_factory=lambda: ["conversation_id", "user_persona", "session_id"]
    )
    
    # Tag-based invalidation
    enable_tags: bool = Field(default=True)
    max_tags_per_entry: int = Field(default=10)
    
    # Observability configuration
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability and monitoring configuration"
    )
    
    # Staleness mitigation
    enable_stale_while_revalidate: bool = Field(
        default=False,
        description="Serve stale data while revalidating in background"
    )
    stale_tolerance_seconds: int = Field(
        default=300,  # 5 minutes
        ge=0,
        description="How long to serve stale data after TTL expires"
    )
    max_stale_age_seconds: int = Field(
        default=3600,  # 1 hour
        ge=0,
        description="Maximum age before refusing to serve stale data"
    )
    enable_version_checking: bool = Field(
        default=False,
        description="Enable version-based cache invalidation"
    )
    cache_version: str = Field(
        default="v1",
        description="Current cache version"
    )
    stale_refresh_callback: Optional[Any] = Field(
        default=None,
        description="Optional async callback for refreshing stale entries: async def callback(prompt, user_id, context) -> str"
    )
    
    # Retry configuration
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        description="Initial retry delay in seconds"
    )
    retry_backoff: float = Field(
        default=2.0,
        ge=1.0,
        description="Retry backoff multiplier"
    )
    
    # L1 Cache
    l1_cache: L1CacheConfig = Field(default_factory=L1CacheConfig)
    
    # Context-aware caching
    enable_context_hashing: bool = Field(default=True)
    context_fields: List[str] = Field(
        default_factory=lambda: ["conversation_id", "user_persona", "session_id"]
    )
    
    # Tag-based invalidation
    enable_tags: bool = Field(default=True)
    max_tags_per_entry: int = Field(default=10)
    
    # Observability
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    # Performance
    connection_pool_size: int = Field(
        default=10,
        ge=1,
        description="Redis connection pool size"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    json_logging: bool = Field(
        default=False,
        description="Use JSON formatted logging"
    )
    
    @field_validator("distance_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("distance_threshold must be between 0.0 and 1.0")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


class CacheSettings(BaseSettings):
    """Environment-based settings for semantic cache."""
    
    model_config = SettingsConfigDict(
        env_prefix="SEMANTIC_CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    redis_url: str = "redis://localhost:6380"
    cache_name: str = "semantic_cache"
    ttl: Optional[int] = 3600
    distance_threshold: float = 0.2
    log_level: str = "INFO"
    
    def to_cache_config(self) -> CacheConfig:
        """Convert settings to CacheConfig."""
        return CacheConfig(
            redis_url=self.redis_url,
            name=self.cache_name,
            ttl=self.ttl,
            distance_threshold=self.distance_threshold,
            log_level=self.log_level,
        )

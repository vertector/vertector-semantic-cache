"""Custom exception hierarchy for semantic cache."""


class SemanticCacheError(Exception):
    """Base exception for all semantic cache errors."""
    pass


class CacheConnectionError(SemanticCacheError):
    """Raised when Redis connection fails."""
    pass


class VectorizerError(SemanticCacheError):
    """Raised when vectorizer operations fail."""
    pass


class RerankerError(SemanticCacheError):
    """Raised when reranker operations fail."""
    pass


class ConfigurationError(SemanticCacheError):
    """Raised when configuration is invalid."""
    pass


class CacheOperationError(SemanticCacheError):
    """Raised when cache operations fail."""
    pass

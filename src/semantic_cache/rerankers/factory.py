"""Reranker factory for creating reranking models."""

from typing import Optional, Any
from redisvl.utils.rerank import (
    BaseReranker,
    HFCrossEncoderReranker,
    CohereReranker,
    VoyageAIReranker,
)

from semantic_cache.core.config import RerankerConfig
from semantic_cache.utils.exceptions import RerankerError
from semantic_cache.utils.logging import get_logger

logger = get_logger(__name__)


class RerankerFactory:
    """Factory for creating reranker instances."""
    
    @staticmethod
    def create(config: RerankerConfig) -> Optional[BaseReranker]:
        """
        Create a reranker instance based on configuration.
        
        Args:
            config: Reranker configuration
            
        Returns:
            Initialized reranker instance, or None if disabled
            
        Raises:
            RerankerError: If reranker creation fails
        """
        if not config.enabled:
            logger.info("Reranker is disabled")
            return None
        
        try:
            logger.info(f"Creating {config.provider} reranker with model: {config.model}")
            
            if config.provider == "huggingface":
                return HFCrossEncoderReranker(
                    model=config.model,
                    limit=config.limit,
                    return_score=config.return_score,
                )
            
            elif config.provider == "cohere":
                api_config = config.api_config or {}
                return CohereReranker(
                    model=config.model,
                    limit=config.limit,
                    return_score=config.return_score,
                    api_config=api_config,
                )
            
            elif config.provider == "voyageai":
                api_config = config.api_config or {}
                return VoyageAIReranker(
                    model=config.model,
                    limit=config.limit,
                    return_score=config.return_score,
                    api_config=api_config,
                )
            
            else:
                raise RerankerError(f"Unknown reranker provider: {config.provider}")
        
        except Exception as e:
            logger.error(f"Failed to create reranker: {e}")
            raise RerankerError(f"Reranker creation failed: {e}") from e
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available reranker providers."""
        return ["huggingface", "cohere", "voyageai"]

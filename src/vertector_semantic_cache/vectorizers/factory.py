"""Vectorizer factory for creating embedding models."""

from typing import Optional, Any
from redisvl.utils.vectorize import (
    BaseVectorizer,
    HFTextVectorizer,
    OpenAITextVectorizer,
    CohereTextVectorizer,
    VertexAITextVectorizer,
    VoyageAITextVectorizer,
    CustomTextVectorizer,
)

from vertector_semantic_cache.core.config import VectorizerConfig
from vertector_semantic_cache.utils.exceptions import VectorizerError
from vertector_semantic_cache.utils.logging import get_logger

logger = get_logger(__name__)


class VectorizerFactory:
    """Factory for creating vectorizer instances."""
    
    @staticmethod
    def create(config: VectorizerConfig) -> BaseVectorizer:
        """
        Create a vectorizer instance based on configuration.
        
        Args:
            config: Vectorizer configuration
            
        Returns:
            Initialized vectorizer instance
            
        Raises:
            VectorizerError: If vectorizer creation fails
        """
        try:
            logger.info(f"Creating {config.provider} vectorizer with model: {config.model}")
            
            if config.provider == "huggingface":
                return HFTextVectorizer(
                    model=config.model,
                    dtype=config.dtype,
                )
            
            elif config.provider == "openai":
                api_config = config.api_config or {}
                return OpenAITextVectorizer(
                    model=config.model,
                    api_config=api_config,
                    dtype=config.dtype,
                    dims=config.dims,
                )
            
            elif config.provider == "cohere":
                api_config = config.api_config or {}
                return CohereTextVectorizer(
                    model=config.model,
                    api_config=api_config,
                    dtype=config.dtype,
                    dims=config.dims,
                )
            
            elif config.provider == "vertexai":
                api_config = config.api_config or {}
                return VertexAITextVectorizer(
                    model=config.model,
                    api_config=api_config,
                    dtype=config.dtype,
                    dims=config.dims,
                )
            
            elif config.provider == "voyageai":
                api_config = config.api_config or {}
                return VoyageAITextVectorizer(
                    model=config.model,
                    api_config=api_config,
                    dtype=config.dtype,
                    dims=config.dims,
                )
            
            elif config.provider == "custom":
                raise VectorizerError(
                    "Custom vectorizer requires manual instantiation. "
                    "Please create CustomTextVectorizer directly."
                )
            
            else:
                raise VectorizerError(f"Unknown vectorizer provider: {config.provider}")
        
        except Exception as e:
            logger.error(f"Failed to create vectorizer: {e}")
            raise VectorizerError(f"Vectorizer creation failed: {e}") from e
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available vectorizer providers."""
        return ["huggingface", "openai", "cohere", "vertexai", "voyageai", "custom"]

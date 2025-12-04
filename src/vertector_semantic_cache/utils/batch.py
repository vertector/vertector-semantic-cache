"""Batch operations module for semantic cache."""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
import time

async def batch_vectorize(texts: List[str], vectorizer) -> List[List[float]]:
    """
    Batch vectorize multiple texts efficiently.
    
    This is more efficient than sequential vectorization because:
    - Single model forward pass
    - GPU batching if available
    - Better throughput
    
    Args:
        texts: List of texts to vectorize
        vectorizer: Vectorizer instance
        
    Returns:
        List of embedding vectors
    """
    # Most vectorizers don't have true async support
    # But batching them is still beneficial
    
    # For now, use the vectorizer's embed method if it supports lists
    if hasattr(vectorizer, 'embed_many'):
        return await vectorizer.embed_many(texts)
    elif hasattr(vectorizer, 'aembed_many'):
        return await vectorizer.aembed_many(texts)
    else:
        # Fall back to sequential (still better than calling check() N times)
        embeddings = []
        for text in texts:
            if hasattr(vectorizer, 'aembed'):
                embedding = await vectorizer.aembed([text])
            else:
                embedding = vectorizer.embed([text])
            embeddings.append(embedding[0] if embedding else [])
        return embeddings

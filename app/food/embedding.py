"""Embedding service for food semantic search.

Uses sentence-transformers with the multi-qa-mpnet-base-dot-v1 model (768-dim).
"""

from typing import List, Optional

# Global model instance (loaded once)
_model = None
_model_name = "sentence-transformers/multi-qa-mpnet-base-dot-v1"


def _load_model():
    """Load the sentence-transformers model lazily."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
        except ImportError as e:
            raise ImportError(
                f"Please install sentence-transformers: pip install sentence-transformers"
            ) from e
    return _model


def _get_embedding_dimension() -> int:
    """Get the dimension of the loaded model."""
    model = _load_model()
    # Use the new method name, fall back to old for compatibility
    if hasattr(model, 'get_embedding_dimension'):
        return model.get_embedding_dimension()
    return model.get_sentence_embedding_dimension()


async def embed_product_text(text: str) -> List[float]:
    """Generate embedding for a product name/text.
    
    Uses sentence-transformers/multi-qa-mpnet-base-dot-v1 (768-dim) for
    semantic search over food products.
    
    Args:
        text: Product name, possibly with brand (e.g., "Chicken Wings KFC")
        
    Returns:
        List of 768 floats (normalized embedding)
    """
    model = _load_model()
    # Run in thread pool to avoid blocking
    import asyncio
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(
        None, 
        lambda: model.encode(text, convert_to_numpy=True, normalize_embeddings=True).tolist()
    )
    return embedding


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts efficiently."""
    model = _load_model()
    import asyncio
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(
        None,
        lambda: model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()
    )
    return embeddings
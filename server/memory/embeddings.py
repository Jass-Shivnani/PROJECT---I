"""
Dione AI — Embeddings Service

Generates vector embeddings locally using sentence-transformers.
All embedding computation happens on-device — no data ever leaves
the user's machine.
"""

from typing import Optional
import numpy as np
from loguru import logger


class EmbeddingService:
    """
    Local embedding generation using sentence-transformers.

    Default model: all-MiniLM-L6-v2 (22M params, very fast on CPU)
    This produces 384-dimensional embeddings good enough for
    semantic similarity and RAG retrieval.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._initialized = False

    async def initialize(self):
        """Load the embedding model."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            self._initialized = True
            logger.info(
                f"Embedding model loaded. Dimension: {self._model.get_sentence_embedding_dimension()}"
            )
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers"
            )

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        if not self._initialized:
            await self.initialize()

        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently."""
        if not self._initialized:
            await self.initialize()

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embedding_dimension(self) -> int:
        """Return the embedding dimension."""
        if self._model:
            return self._model.get_sentence_embedding_dimension()
        # Default for all-MiniLM-L6-v2
        return 384

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))

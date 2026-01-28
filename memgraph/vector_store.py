"""
Abstract interface for vector storage and similarity search.

Provides database-agnostic interface for storing and querying
embedding vectors, with concrete implementations for SQLite.
"""

from abc import ABC, abstractmethod
import numpy as np


class VectorStore(ABC):
    """
    Abstract interface for vector storage and similarity search.

    Implementations provide efficient storage and k-nearest-neighbor
    search for embedding vectors.
    """

    @abstractmethod
    def add(
        self,
        entity_id: str,
        embedding: np.ndarray,
        model_name: str,
    ) -> None:
        """
        Store an embedding vector.

        Args:
            entity_id: Unique identifier for the entity
            embedding: Embedding vector as numpy array
            model_name: Model that generated this embedding
        """
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        threshold: float = 0.0,
        model_name: str | None = None,
    ) -> list[tuple[str, float]]:
        """
        Search for similar vectors using cosine similarity.

        Args:
            query_embedding: Query vector
            k: Number of results to return
            threshold: Minimum similarity score (0-1)
            model_name: Only search embeddings from this model

        Returns:
            List of (entity_id, similarity_score) tuples, sorted by score descending
        """
        pass

    @abstractmethod
    def get(self, entity_id: str) -> tuple[np.ndarray, str] | None:
        """
        Retrieve embedding for an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            Tuple of (embedding, model_name) or None if not found
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> None:
        """
        Remove an embedding.

        Args:
            entity_id: Entity identifier
        """
        pass

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """
        Check if embedding exists for entity.

        Args:
            entity_id: Entity identifier

        Returns:
            True if embedding exists
        """
        pass

    @abstractmethod
    def count(self, model_name: str | None = None) -> int:
        """
        Count stored embeddings.

        Args:
            model_name: Only count embeddings from this model

        Returns:
            Number of stored embeddings
        """
        pass

    @abstractmethod
    def batch_add(
        self,
        entity_ids: list[str],
        embeddings: list[np.ndarray],
        model_name: str,
    ) -> None:
        """
        Store multiple embeddings efficiently.

        Args:
            entity_ids: List of entity identifiers
            embeddings: List of embedding vectors
            model_name: Model that generated these embeddings
        """
        pass


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Similarity score between 0 and 1 (1 = identical direction)
    """
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))

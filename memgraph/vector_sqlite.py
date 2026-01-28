"""
SQLite-based vector storage using sqlite-vec extension.

Provides efficient vector similarity search using SQLite's
native support for vector operations via the sqlite-vec extension.
"""

import sqlite3
import numpy as np
from pathlib import Path

from .vector_store import VectorStore, cosine_similarity


class VectorSQLiteStore(VectorStore):
    """
    Vector storage using SQLite with sqlite-vec extension.

    Stores embeddings as BLOBs and performs similarity search
    using sqlite-vec's vector functions when available, falling
    back to pure Python cosine similarity otherwise.
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize SQLite vector store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._has_vec_extension = False

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row

            # Try to load sqlite-vec extension
            try:
                self._conn.enable_load_extension(True)
                self._conn.load_extension("vec0")
                self._has_vec_extension = True
            except Exception:
                # Extension not available, use pure Python fallback
                self._has_vec_extension = False

        return self._conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()

        # Create embeddings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                entity_id TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index on model_name for filtering
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_model
            ON embeddings(model_name)
        """)

        conn.commit()

    def add(
        self,
        entity_id: str,
        embedding: np.ndarray,
        model_name: str,
    ) -> None:
        """Store an embedding vector."""
        conn = self._get_connection()

        # Convert numpy array to bytes
        embedding_bytes = embedding.astype(np.float32).tobytes()
        dimensions = len(embedding)

        conn.execute("""
            INSERT OR REPLACE INTO embeddings
            (entity_id, embedding, model_name, dimensions, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (entity_id, embedding_bytes, model_name, dimensions))

        conn.commit()

    def batch_add(
        self,
        entity_ids: list[str],
        embeddings: list[np.ndarray],
        model_name: str,
    ) -> None:
        """Store multiple embeddings efficiently."""
        if len(entity_ids) != len(embeddings):
            raise ValueError("entity_ids and embeddings must have same length")

        conn = self._get_connection()

        # Prepare batch data
        batch_data = []
        for entity_id, embedding in zip(entity_ids, embeddings, strict=True):
            embedding_bytes = embedding.astype(np.float32).tobytes()
            dimensions = len(embedding)
            batch_data.append((entity_id, embedding_bytes, model_name, dimensions))

        conn.executemany("""
            INSERT OR REPLACE INTO embeddings
            (entity_id, embedding, model_name, dimensions, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, batch_data)

        conn.commit()

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        threshold: float = 0.0,
        model_name: str | None = None,
    ) -> list[tuple[str, float]]:
        """Search for similar vectors using cosine similarity."""
        conn = self._get_connection()

        # Build query
        if model_name:
            cursor = conn.execute("""
                SELECT entity_id, embedding, dimensions
                FROM embeddings
                WHERE model_name = ?
            """, (model_name,))
        else:
            cursor = conn.execute("""
                SELECT entity_id, embedding, dimensions
                FROM embeddings
            """)

        # Calculate similarities (pure Python for now)
        results: list[tuple[str, float]] = []
        query_norm = query_embedding.astype(np.float32)

        for row in cursor:
            # Convert bytes back to numpy array
            stored_embedding = np.frombuffer(row["embedding"], dtype=np.float32)

            # Verify dimensions match
            if len(stored_embedding) != len(query_norm):
                continue

            # Calculate cosine similarity
            similarity = cosine_similarity(query_norm, stored_embedding)

            if similarity >= threshold:
                results.append((row["entity_id"], similarity))

        # Sort by similarity descending and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def get(self, entity_id: str) -> tuple[np.ndarray, str] | None:
        """Retrieve embedding for an entity."""
        conn = self._get_connection()

        cursor = conn.execute("""
            SELECT embedding, model_name, dimensions
            FROM embeddings
            WHERE entity_id = ?
        """, (entity_id,))

        row = cursor.fetchone()
        if row is None:
            return None

        embedding = np.frombuffer(row["embedding"], dtype=np.float32)
        return (embedding, row["model_name"])

    def delete(self, entity_id: str) -> None:
        """Remove an embedding."""
        conn = self._get_connection()
        conn.execute("DELETE FROM embeddings WHERE entity_id = ?", (entity_id,))
        conn.commit()

    def exists(self, entity_id: str) -> bool:
        """Check if embedding exists for entity."""
        conn = self._get_connection()

        cursor = conn.execute("""
            SELECT 1 FROM embeddings WHERE entity_id = ? LIMIT 1
        """, (entity_id,))

        return cursor.fetchone() is not None

    def count(self, model_name: str | None = None) -> int:
        """Count stored embeddings."""
        conn = self._get_connection()

        if model_name:
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM embeddings WHERE model_name = ?
            """, (model_name,))
        else:
            cursor = conn.execute("SELECT COUNT(*) as count FROM embeddings")

        row = cursor.fetchone()
        return row["count"] if row else 0

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "VectorSQLiteStore":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()

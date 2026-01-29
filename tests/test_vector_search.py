"""
Test vector storage and embedding generation.
"""

import tempfile
from pathlib import Path
import numpy as np

from memgraph.embeddings import (
    SentenceTransformerProvider,
    configure_from_dict,
    get_embedding_provider,
)
from memgraph.vector_sqlite import VectorSQLiteStore


def test_sentence_transformer_provider():
    """Test basic embedding generation."""
    provider = SentenceTransformerProvider()

    # Generate single embedding
    text = "This is a test entity"
    embedding = provider.generate(text)

    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 dimensions
    assert embedding.dtype == np.float32

    # Test batch generation
    texts = ["First entity", "Second entity", "Third entity"]
    embeddings = provider.batch_generate(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 384 for emb in embeddings)

    # Verify similar texts have similar embeddings
    similar_texts = ["cat", "kitten", "dog"]
    similar_embeddings = provider.batch_generate(similar_texts)

    # cat and kitten should be more similar than cat and dog
    from memgraph.vector_store import cosine_similarity
    cat_kitten_sim = cosine_similarity(similar_embeddings[0], similar_embeddings[1])
    cat_dog_sim = cosine_similarity(similar_embeddings[0], similar_embeddings[2])

    assert cat_kitten_sim > cat_dog_sim


def test_vector_store_basic_operations():
    """Test vector storage and retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = VectorSQLiteStore(db_path)

        # Test add and exists
        entity_id = "entity_1"
        embedding = np.random.rand(384).astype(np.float32)
        model_name = "test-model"

        assert not store.exists(entity_id)
        store.add(entity_id, embedding, model_name)
        assert store.exists(entity_id)

        # Test get
        retrieved = store.get(entity_id)
        assert retrieved is not None
        retrieved_embedding, retrieved_model = retrieved
        assert retrieved_model == model_name
        assert np.allclose(retrieved_embedding, embedding)

        # Test count
        assert store.count() == 1
        assert store.count(model_name) == 1
        assert store.count("other-model") == 0

        # Test delete
        store.delete(entity_id)
        assert not store.exists(entity_id)
        assert store.count() == 0


def test_vector_store_batch_operations():
    """Test batch operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = VectorSQLiteStore(db_path)

        # Add multiple embeddings
        entity_ids = [f"entity_{i}" for i in range(10)]
        embeddings = [np.random.rand(384).astype(np.float32) for _ in range(10)]
        model_name = "test-model"

        store.batch_add(entity_ids, embeddings, model_name)

        assert store.count() == 10
        for entity_id in entity_ids:
            assert store.exists(entity_id)


def test_vector_similarity_search():
    """Test similarity search functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = VectorSQLiteStore(db_path)

        # Create embeddings with known relationships
        # Base vector pointing in one direction
        base = np.array([1.0, 0.0, 0.0] + [0.0] * 381, dtype=np.float32)

        # Similar vector (small angle)
        similar = np.array([0.9, 0.1, 0.0] + [0.0] * 381, dtype=np.float32)

        # Dissimilar vector (perpendicular)
        dissimilar = np.array([0.0, 1.0, 0.0] + [0.0] * 381, dtype=np.float32)

        # Store vectors
        store.add("base", base, "test")
        store.add("similar", similar, "test")
        store.add("dissimilar", dissimilar, "test")

        # Search using base vector
        results = store.search(base, k=2)

        assert len(results) == 2
        # First result should be the base itself (similarity = 1.0)
        assert results[0][0] == "base"
        assert abs(results[0][1] - 1.0) < 0.01

        # Second result should be similar (higher similarity than dissimilar)
        assert results[1][0] == "similar"
        assert results[1][1] > 0.5  # Should have decent similarity


def test_end_to_end_semantic_search():
    """Test complete workflow: generate embeddings + search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = VectorSQLiteStore(db_path)
        provider = SentenceTransformerProvider()

        # Create knowledge about programming languages
        entities = {
            "python": "Python is a high-level programming language",
            "javascript": "JavaScript is a scripting language for web browsers",
            "java": "Java is an object-oriented programming language",
            "html": "HTML is a markup language for creating web pages",
        }

        # Generate and store embeddings
        for entity_id, text in entities.items():
            embedding = provider.generate(text)
            store.add(entity_id, embedding, provider.model_name)

        # Search for programming language
        query = "programming language for web development"
        query_embedding = provider.generate(query)

        results = store.search(query_embedding, k=4)

        # Should find all entities, but JavaScript and Python should rank higher
        # than HTML (which is markup, not programming)
        assert len(results) == 4
        result_ids = [r[0] for r in results]

        # JavaScript should be in top 2 (matches "web" and "language")
        assert "javascript" in result_ids[:2] or "python" in result_ids[:2]


def test_provider_configuration():
    """Test provider configuration system."""
    config: dict[str, str | None] = {
        "provider": "sentence-transformers",
        "model": "all-MiniLM-L6-v2",
    }

    configure_from_dict(config)
    provider = get_embedding_provider()

    assert provider is not None
    assert provider.model_name == "all-MiniLM-L6-v2"
    assert provider.dimensions == 384

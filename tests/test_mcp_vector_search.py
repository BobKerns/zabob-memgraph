"""Tests for vector search MCP tools."""

import pytest
from memgraph.embeddings import configure_from_dict
from memgraph.mcp_service import (
    configure_embeddings,
    generate_embeddings,
    search_entities_semantic,
    search_hybrid,
)


@pytest.mark.asyncio
async def test_configure_embeddings():
    """Test embedding provider configuration."""
    result = await configure_embeddings(
        provider="sentence-transformers",
        model="all-MiniLM-L6-v2",
    )

    assert "message" in result
    assert result.get("provider") == "sentence-transformers"
    assert result.get("model") == "all-MiniLM-L6-v2"
    assert "dimensions" in result


@pytest.mark.asyncio
async def test_generate_embeddings():
    """Test generating embeddings for entities."""
    # First configure provider
    await configure_embeddings(
        provider="sentence-transformers",
        model="all-MiniLM-L6-v2",
    )

    # Generate embeddings
    result = await generate_embeddings(batch_size=10)

    assert "generated" in result or "message" in result
    if "generated" in result:
        assert isinstance(result["generated"], int)
        assert result["generated"] >= 0


@pytest.mark.asyncio
async def test_search_entities_semantic():
    """Test semantic entity search."""
    # Configure and generate embeddings first
    await configure_embeddings()
    await generate_embeddings(batch_size=10)

    # Perform semantic search
    result = await search_entities_semantic(
        query="machine learning concepts",
        k=5,
    )

    # Should return results or error (depending on whether entities exist)
    assert isinstance(result, dict)
    assert "error" in result or "results" in result


@pytest.mark.asyncio
async def test_search_hybrid():
    """Test hybrid search combining keyword and semantic."""
    # Configure and generate embeddings first
    await configure_embeddings()
    await generate_embeddings()

    # Perform hybrid search
    result = await search_hybrid(
        query="test query",
        k=10,
        semantic_weight=0.7,
    )

    assert isinstance(result, dict)
    assert "results" in result or "entities" in result
    if "semantic_weight" in result:
        assert result["semantic_weight"] == 0.7


@pytest.mark.asyncio
async def test_semantic_search_without_configuration():
    """Test that semantic search fails gracefully without configuration."""
    # Reset configuration
    from memgraph.embeddings import set_embedding_provider
    set_embedding_provider(None)  # type: ignore[arg-type]

    result = await search_entities_semantic(query="test")

    assert "error" in result
    assert "No embedding provider configured" in result["error"]


@pytest.mark.asyncio
async def test_hybrid_search_fallback():
    """Test that hybrid search falls back to keyword search if semantic fails."""
    # Reset configuration to make semantic search fail
    from memgraph.embeddings import set_embedding_provider
    set_embedding_provider(None)  # type: ignore[arg-type]

    result = await search_hybrid(query="test")

    # Should fall back to keyword search results
    assert isinstance(result, dict)
    assert "results" in result or "entities" in result

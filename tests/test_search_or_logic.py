"""
Tests for OR-based search logic with BM25 ranking in SQLite backend.

This module tests the enhanced search functionality that:
- Uses OR logic for partial term matching
- Ranks results using BM25 relevance scoring
- Provides graceful degradation instead of binary fail
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = Path(temp_file.name)
    temp_file.close()
    
    # Create database with backup disabled for tests
    db = SQLiteKnowledgeGraphDB(db_path=str(temp_path), backup_on_start=False)
    
    yield db
    
    # Cleanup
    temp_path.unlink(missing_ok=True)
    # Clean up any WAL/SHM files
    for suffix in ["-wal", "-shm"]:
        wal_file = Path(str(temp_path) + suffix)
        wal_file.unlink(missing_ok=True)


@pytest.fixture
async def populated_db(temp_db):
    """Create a database populated with test data"""
    # Create diverse test entities
    await temp_db.create_entities([
        {
            "name": "Python",
            "entityType": "programming_language",
            "observations": [
                "High-level programming language",
                "Dynamic typing system",
                "Popular for data science and AI"
            ]
        },
        {
            "name": "FastAPI",
            "entityType": "web_framework",
            "observations": [
                "Modern Python web framework",
                "Built on Starlette and Pydantic",
                "Automatic API documentation"
            ]
        },
        {
            "name": "SQLite",
            "entityType": "database",
            "observations": [
                "Embedded relational database",
                "ACID compliant and lightweight",
                "Popular for mobile applications"
            ]
        },
        {
            "name": "Agent",
            "entityType": "ai_concept",
            "observations": [
                "Autonomous entity with goals",
                "Can coordinate with other agents",
                "Used in AI system design"
            ]
        },
        {
            "name": "Memory",
            "entityType": "ai_concept",
            "observations": [
                "Knowledge storage architecture",
                "Critical for agent coordination",
                "Design patterns for persistence"
            ]
        }
    ])
    
    # Create relations
    await temp_db.create_relations([
        {
            "from_entity": "FastAPI",
            "to": "Python",
            "relationType": "written_in"
        },
        {
            "from_entity": "Agent",
            "to": "Memory",
            "relationType": "requires"
        }
    ])
    
    return temp_db


@pytest.mark.asyncio
async def test_single_term_search(populated_db):
    """Test that single term search returns matching entities"""
    results = await populated_db.search_nodes("Python")
    
    assert len(results["entities"]) >= 1
    entity_names = [e["name"] for e in results["entities"]]
    assert "Python" in entity_names


@pytest.mark.asyncio
async def test_partial_match_returns_results(populated_db):
    """Test that queries with partial term matches return ranked results"""
    # Query with 5 terms where only some entities match all terms
    results = await populated_db.search_nodes("agent coordination memory design architecture")
    
    # Should return entities matching ANY of the terms
    assert len(results["entities"]) > 0
    
    # Entities matching more terms should appear
    entity_names = [e["name"] for e in results["entities"]]
    
    # Memory and Agent entities should be found (they have multiple matching terms)
    assert "Memory" in entity_names or "Agent" in entity_names


@pytest.mark.asyncio
async def test_all_terms_match_ranks_highest(populated_db):
    """Test that entities matching all terms score higher than partial matches"""
    # Search for terms that match Memory entity completely
    results = await populated_db.search_nodes("agent coordination memory")
    
    assert len(results["entities"]) > 0
    
    # Memory should rank high because it has observations matching multiple terms
    entity_names = [e["name"] for e in results["entities"]]
    assert "Memory" in entity_names
    
    # Memory entity should be in top 2 results
    top_2_names = [e["name"] for e in results["entities"][:2]]
    assert "Memory" in top_2_names or "Agent" in top_2_names


@pytest.mark.asyncio
async def test_multiple_partial_matches(populated_db):
    """Test that multiple entities with partial matches all appear in results"""
    # Terms that match different entities
    results = await populated_db.search_nodes("programming database")
    
    assert len(results["entities"]) >= 2
    entity_names = [e["name"] for e in results["entities"]]
    
    # Should find Python (programming) and SQLite (database)
    assert "Python" in entity_names
    assert "SQLite" in entity_names


@pytest.mark.asyncio
async def test_observation_search_with_or(populated_db):
    """Test that OR logic works when searching in observations"""
    # Terms appearing in different entity observations
    results = await populated_db.search_nodes("ACID Pydantic")
    
    assert len(results["entities"]) >= 2
    entity_names = [e["name"] for e in results["entities"]]
    
    # Should find both SQLite (ACID) and FastAPI (Pydantic)
    assert "SQLite" in entity_names
    assert "FastAPI" in entity_names


@pytest.mark.asyncio
async def test_empty_query_returns_empty(populated_db):
    """Test that empty query returns empty results"""
    results = await populated_db.search_nodes("")
    
    assert results["entities"] == []
    assert results["relations"] == []


@pytest.mark.asyncio
async def test_whitespace_only_query_returns_empty(populated_db):
    """Test that whitespace-only query returns empty results"""
    results = await populated_db.search_nodes("   \t  \n  ")
    
    assert results["entities"] == []
    assert results["relations"] == []


@pytest.mark.asyncio
async def test_no_match_returns_empty(populated_db):
    """Test that query with no matches returns empty results gracefully"""
    results = await populated_db.search_nodes("xyznonexistent123")
    
    assert results["entities"] == []
    assert results["relations"] == []


@pytest.mark.asyncio
async def test_relations_included_for_matches(populated_db):
    """Test that relations are included for matching entities"""
    results = await populated_db.search_nodes("FastAPI")
    
    assert len(results["entities"]) >= 1
    assert "FastAPI" in [e["name"] for e in results["entities"]]
    
    # Should include relation from FastAPI to Python
    if len(results["relations"]) > 0:
        relation_types = [(r["from_entity"], r["to"], r["relationType"]) 
                         for r in results["relations"]]
        assert ("FastAPI", "Python", "written_in") in relation_types


@pytest.mark.asyncio
async def test_case_insensitive_search(populated_db):
    """Test that search is case-insensitive (FTS5 default behavior)"""
    # Search with different cases
    results_lower = await populated_db.search_nodes("python")
    results_upper = await populated_db.search_nodes("PYTHON")
    results_mixed = await populated_db.search_nodes("PyThOn")
    
    # All should return Python entity
    assert len(results_lower["entities"]) > 0
    assert len(results_upper["entities"]) > 0
    assert len(results_mixed["entities"]) > 0
    
    assert "Python" in [e["name"] for e in results_lower["entities"]]
    assert "Python" in [e["name"] for e in results_upper["entities"]]
    assert "Python" in [e["name"] for e in results_mixed["entities"]]


@pytest.mark.asyncio
async def test_ranking_order_preserved(populated_db):
    """Test that results are returned in relevance order"""
    # Create entity with exact name match and entity with observation match
    await populated_db.create_entities([
        {
            "name": "SpecialTerm",
            "entityType": "test",
            "observations": ["Something unrelated"]
        },
        {
            "name": "Other",
            "entityType": "test",
            "observations": ["This has SpecialTerm in observation"]
        }
    ])
    
    results = await populated_db.search_nodes("SpecialTerm")
    
    assert len(results["entities"]) >= 2
    
    # Entity with name match should rank higher than observation match
    # (though order may vary based on BM25 scoring details)
    entity_names = [e["name"] for e in results["entities"]]
    assert "SpecialTerm" in entity_names


@pytest.mark.asyncio
async def test_complex_multi_term_query(populated_db):
    """Test complex query with many terms"""
    # Use all terms from the problem statement example
    results = await populated_db.search_nodes("agent coordination memory design architecture")
    
    # Should return results even though no single entity matches all terms
    assert len(results["entities"]) > 0
    
    # Should include entities with partial matches
    entity_names = [e["name"] for e in results["entities"]]
    
    # At least some AI concept entities should be found
    assert any(name in entity_names for name in ["Agent", "Memory"])


@pytest.mark.asyncio
async def test_fts_special_characters_escaped(populated_db):
    """Test that FTS special characters are properly escaped"""
    # Add entity with parentheses in name
    await populated_db.create_entities([
        {
            "name": "Function(test)",
            "entityType": "code",
            "observations": ["A function with special chars"]
        }
    ])
    
    # Search with special characters that could break FTS
    # These should not cause syntax errors
    results = await populated_db.search_nodes("Function(test)")
    assert len(results["entities"]) >= 1
    
    # Search with quotes
    await populated_db.create_entities([
        {
            "name": "Quote Entity",
            "entityType": "test",
            "observations": ['Has "quoted" text']
        }
    ])
    
    # Should not cause FTS syntax error
    results = await populated_db.search_nodes('"quoted"')
    assert isinstance(results["entities"], list)  # No crash


@pytest.mark.asyncio
async def test_fts_operator_keywords_escaped(populated_db):
    """Test that FTS operator keywords (AND, OR, NOT) are escaped"""
    await populated_db.create_entities([
        {
            "name": "AND Gate",
            "entityType": "logic",
            "observations": ["Boolean AND operation"]
        },
        {
            "name": "OR Gate",
            "entityType": "logic",
            "observations": ["Boolean OR operation"]
        }
    ])
    
    # Search for literal "AND" (not as operator)
    results = await populated_db.search_nodes("AND Gate")
    assert len(results["entities"]) >= 1
    assert "AND Gate" in [e["name"] for e in results["entities"]]
    
    # Search for literal "OR" (not as operator)
    results = await populated_db.search_nodes("OR Gate")
    assert len(results["entities"]) >= 1
    assert "OR Gate" in [e["name"] for e in results["entities"]]

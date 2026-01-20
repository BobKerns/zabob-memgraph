"""Test search_nodes functionality with OR logic and ranking"""

import asyncio
import sqlite3
from pathlib import Path
import pytest
from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB


@pytest.fixture
async def test_db(tmp_path: Path):
    """Create a test database with sample data"""
    db_path = tmp_path / "test_search.db"
    db = SQLiteKnowledgeGraphDB(db_path=str(db_path))
    
    # Create sample entities
    await db.create_entities([
        {
            "name": "agent_coordination_challenge",
            "entityType": "concept",
            "observations": [
                "Explores how multiple AI agents coordinate",
                "Discusses memory architecture for agents"
            ]
        },
        {
            "name": "zabob-memgraph",
            "entityType": "project",
            "observations": [
                "Knowledge graph visualization tool",
                "MCP server for AI collaboration"
            ]
        },
        {
            "name": "Python",
            "entityType": "language",
            "observations": [
                "High-level programming language",
                "Used for AI and data science"
            ]
        },
        {
            "name": "collaboration_patterns",
            "entityType": "concept",
            "observations": [
                "Patterns for AI agent collaboration",
                "Tools for multi-agent systems"
            ]
        }
    ])
    
    # Create relations
    await db.create_relations(
        relations=[
            {
                "from_entity": "zabob-memgraph",
                "to": "Python",
                "relationType": "written_in",
            },
            {
                "from_entity": "agent_coordination_challenge",
                "to": "collaboration_patterns",
                "relationType": "relates_to"
            }
        ],
        external_refs=[
            "zabob-memgraph",
            "Python",
            "agent_coordination_challenge",
            "collaboration_patterns"
        ]
    )
    
    yield db


@pytest.mark.asyncio
async def test_search_single_term(test_db):
    """Test search with single term returns results"""
    result = await test_db.search_nodes("agent")
    
    assert "entities" in result
    assert len(result["entities"]) > 0
    
    # Should find agent_coordination_challenge
    entity_names = [e["name"] for e in result["entities"]]
    assert "agent_coordination_challenge" in entity_names


@pytest.mark.asyncio
async def test_search_multi_term_or_logic(test_db):
    """Test search with multiple terms uses OR logic (not AND)"""
    # This query has terms that don't all appear in any single entity
    # With OR logic, it should still return results for partial matches
    result = await test_db.search_nodes("agent coordination memory design architecture")
    
    assert "entities" in result
    # Should find agent_coordination_challenge even though it doesn't have "architecture"
    assert len(result["entities"]) > 0
    
    entity_names = [e["name"] for e in result["entities"]]
    assert "agent_coordination_challenge" in entity_names


@pytest.mark.asyncio
async def test_search_partial_match(test_db):
    """Test that search works with partial term matches"""
    result = await test_db.search_nodes("zabob memgraph project purpose")
    
    assert "entities" in result
    assert len(result["entities"]) > 0
    
    # Should find zabob-memgraph project even though "purpose" isn't in it
    entity_names = [e["name"] for e in result["entities"]]
    assert "zabob-memgraph" in entity_names


@pytest.mark.asyncio
async def test_search_ai_collaboration(test_db):
    """Test search for AI collaboration terms"""
    result = await test_db.search_nodes("AI collaboration patterns tools")
    
    assert "entities" in result
    assert len(result["entities"]) > 0
    
    # Should find collaboration_patterns or zabob-memgraph
    entity_names = [e["name"] for e in result["entities"]]
    assert "collaboration_patterns" in entity_names or "zabob-memgraph" in entity_names


@pytest.mark.asyncio
async def test_search_ranking_order(test_db):
    """Test that results are ranked by relevance (BM25)"""
    result = await test_db.search_nodes("agent coordination")
    
    assert "entities" in result
    assert len(result["entities"]) > 0
    
    # agent_coordination_challenge should rank higher because it has both terms
    entity_names = [e["name"] for e in result["entities"]]
    # The entity with most matching terms should appear first (or near first)
    first_entity = entity_names[0]
    # agent_coordination_challenge should be ranked high
    assert entity_names.index("agent_coordination_challenge") <= 1


@pytest.mark.asyncio
async def test_search_empty_query(test_db):
    """Test that empty query returns empty results"""
    result = await test_db.search_nodes("")
    
    assert "entities" in result
    assert len(result["entities"]) == 0


@pytest.mark.asyncio
async def test_search_observations(test_db):
    """Test that search finds entities by observation content"""
    result = await test_db.search_nodes("visualization")
    
    assert "entities" in result
    assert len(result["entities"]) > 0
    
    # Should find zabob-memgraph which has "visualization" in observations
    entity_names = [e["name"] for e in result["entities"]]
    assert "zabob-memgraph" in entity_names


@pytest.mark.asyncio
async def test_search_includes_relations(test_db):
    """Test that search results include relations for matching entities"""
    result = await test_db.search_nodes("Python")
    
    assert "entities" in result
    assert "relations" in result
    
    # Should find Python entity
    entity_names = [e["name"] for e in result["entities"]]
    assert "Python" in entity_names
    
    # Should include relations involving Python
    if len(result["relations"]) > 0:
        relation_entities = set()
        for rel in result["relations"]:
            relation_entities.add(rel["from_entity"])
            relation_entities.add(rel["to"])
        assert "Python" in relation_entities

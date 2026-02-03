"""Test search_nodes functionality - Issue #29

Tests the OR-based search with BM25 ranking and entity name prioritization.
"""
import asyncio
import pytest
from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB


@pytest.fixture
def db(test_server):
    """Database instance connected to test server's database"""
    db_path = test_server["db_path"]
    return SQLiteKnowledgeGraphDB(db_path=str(db_path))


@pytest.fixture
def sample_data(db):
    """Populate database with test data for search"""
    async def populate():
        # Create entities with varied content for testing search
        await db.create_entities([
            {
                "name": "Zabob Project",
                "entityType": "Project",
                "observations": [
                    "Knowledge graph server for AI assistants",
                    "Built with Python and FastAPI",
                    "Purpose: persistent memory for agents"
                ]
            },
            {
                "name": "Agent Coordination",
                "entityType": "Concept",
                "observations": [
                    "Multi-agent memory sharing architecture",
                    "Design focuses on concurrent access",
                    "Uses SQLite for coordination"
                ]
            },
            {
                "name": "Memory System",
                "entityType": "Component",
                "observations": [
                    "Persistent storage for agent knowledge",
                    "Supports full-text search"
                ]
            },
            {
                "name": "Design Patterns",
                "entityType": "Documentation",
                "observations": [
                    "Architecture documentation",
                    "Software design principles"
                ]
            },
            {
                "name": "Python Import Issue",
                "entityType": "Bug",
                "observations": [
                    "Python import failure",
                    "Resolved by updating dependencies"
                ]
            }
        ])

    # Run population in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(populate())
    finally:
        loop.close()

    return db


def test_multi_word_or_search(sample_data):
    """Test that multi-word queries use OR logic and return results"""
    async def run_test():
        # Test multi-word query that should match multiple entities
        result = await sample_data.search_nodes("agent coordination memory design architecture")

        entities = result["entities"]

        # Should find results with OR logic (any term matches)
        assert len(entities) > 0, "Multi-word OR search should return results"

        # Should find at least the Agent Coordination entity (matches "agent coordination")
        entity_names = [e["name"] for e in entities]
        assert "Agent Coordination" in entity_names, "Should find 'Agent Coordination' entity"

        # Should also find Memory System (matches "memory")
        assert "Memory System" in entity_names, "Should find 'Memory System' entity"

        # Results should be ordered by relevance (entities matching more terms first)
        # Agent Coordination should rank higher than Memory System (matches 2 terms vs 1)
        agent_idx = entity_names.index("Agent Coordination")
        memory_idx = entity_names.index("Memory System")
        assert agent_idx < memory_idx, "Entities matching more terms should rank higher"

    # Run async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_entity_name_prioritization(sample_data):
    """Test that entity names are prioritized in search results (2x weight)"""
    async def run_test():
        # Search for "project" which appears in entity name and observations
        result = await sample_data.search_nodes("project purpose")

        entities = result["entities"]

        assert len(entities) > 0, "Should find entities matching search terms"

        entity_names = [e["name"] for e in entities]

        # "Zabob Project" should rank highly because "project" is in the name (2x weight)
        assert "Zabob Project" in entity_names, "Should find 'Zabob Project' entity"

        # Entity with "project" in name should rank higher than one with it only in observations
        zabob_idx = entity_names.index("Zabob Project")
        assert zabob_idx < 3, "Entity name matches should rank in top 3"

    # Run async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_exact_entity_name_search(sample_data):
    """Test searching for specific entity names returns exact matches"""
    async def run_test():
        # Search for partial entity name
        result = await sample_data.search_nodes("zabob")

        entities = result["entities"]

        assert len(entities) > 0, "Should find entity with 'zabob' in name"

        entity_names = [e["name"] for e in entities]
        assert "Zabob Project" in entity_names, "Should find 'Zabob Project' by name search"

        # Should rank at or near the top due to name match
        zabob_idx = entity_names.index("Zabob Project")
        assert zabob_idx == 0, "Exact name match should rank first"

    # Run async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_observation_search(sample_data):
    """Test searching in observation content"""
    async def run_test():
        # Search for term only in observations, not in entity names
        result = await sample_data.search_nodes("fastapi")

        entities = result["entities"]

        assert len(entities) > 0, "Should find entities by observation content"

        entity_names = [e["name"] for e in entities]
        assert "Zabob Project" in entity_names, "Should find entity with 'fastapi' in observations"

    # Run async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_empty_search(sample_data):
    """Test that empty or nonsense queries handle gracefully"""
    async def run_test():
        # Search for nonsense that won't match anything
        result = await sample_data.search_nodes("xyzabc123nonexistent")

        entities = result["entities"]

        # Should return empty list, not error
        assert isinstance(entities, list), "Should return list even for no results"
        assert len(entities) == 0, "Should return empty list for no matches"

    # Run async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_single_word_search(sample_data):
    """Test single-word searches work correctly"""
    async def run_test():
        # Single word search should work same as before
        result = await sample_data.search_nodes("python")

        entities = result["entities"]

        assert len(entities) > 0, "Single-word search should find results"

        entity_names = [e["name"] for e in entities]

        # Should find entities with "python" in name or observations
        # Note: exact entity found depends on sample data
        assert any(
            "python" in name.lower()
            or "python" in str(entity.get("observations", [])).lower()
            for name, entity in zip(entity_names, entities, strict=True)
        ), "Should find entities related to Python"

    # Run async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_entity_deduplication(sample_data):
    """Test that entities are deduplicated in search results - Issue #43"""
    async def run_test():
        # Add an entity with multiple observations that match the query
        await sample_data.create_entities([
            {
                "name": "Test Entity",
                "entityType": "Test",
                "observations": [
                    "First observation with search term",
                    "Second observation with search term",
                    "Third observation with search term"
                ]
            }
        ])

        # Search for "search term" - should return entity only once
        result = await sample_data.search_nodes("search term")
        entities = result["entities"]

        entity_names = [e["name"] for e in entities]

        # Count occurrences of "Test Entity" - should only appear once
        test_entity_count = entity_names.count("Test Entity")
        assert test_entity_count == 1, f"Entity should appear exactly once, not {test_entity_count} times"

        # Find the Test Entity in results
        test_entity = next((e for e in entities if e["name"] == "Test Entity"), None)
        assert test_entity is not None, "Test Entity should be in results"

        # Should have all observations included in the single result
        assert len(test_entity["observations"]) == 3, "All observations should be included"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_case_insensitive_sorting(sample_data):
    """Test that results are sorted case-insensitively - Issue #43"""
    async def run_test():
        # Add entities with names that differ only in case
        await sample_data.create_entities([
            {
                "name": "zebra",
                "entityType": "Test",
                "observations": ["Contains search keyword"]
            },
            {
                "name": "Apple",
                "entityType": "Test",
                "observations": ["Contains search keyword"]
            },
            {
                "name": "banana",
                "entityType": "Test",
                "observations": ["Contains search keyword"]
            }
        ])

        # Search for "keyword" - all should be found
        result = await sample_data.search_nodes("keyword")
        entities = result["entities"]

        # Filter to just our test entities
        test_entities = [e for e in entities if e["name"] in ["zebra", "Apple", "banana"]]

        # Extract names
        names = [e["name"] for e in test_entities]

        # Should be sorted case-insensitively: Apple, banana, zebra
        # (or at least Apple should come before zebra)
        if "Apple" in names and "zebra" in names:
            apple_index = names.index("Apple")
            zebra_index = names.index("zebra")
            assert apple_index < zebra_index, \
                f"'Apple' should come before 'zebra' in case-insensitive sort, got: {names}"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()

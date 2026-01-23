"""Test that matching observations appear first in search results."""

import asyncio
import pytest
from memgraph.sqlite_backend import SQLiteKnowledgeGraphDB


@pytest.fixture
def db(test_server):
    """Database instance connected to test server's database"""
    db_path = test_server["db_path"]
    return SQLiteKnowledgeGraphDB(db_path=str(db_path))


def test_matching_observations_sorted_first(db):
    """Test that observations matching search query appear before non-matching ones."""

    async def run_test():
        # Create entity with multiple observations, only some matching
        await db.create_entities([
            {
                "name": "TestEntity",
                "entityType": "Test",
                "observations": [
                    "First observation without keyword",
                    "Second observation with TARGET word",
                    "Third observation without keyword",
                    "Fourth observation with TARGET word",
                    "Fifth observation without keyword",
                ]
            }
        ])

        # Search for "TARGET"
        result = await db.search_nodes("TARGET")
        entities = result["entities"]

        # Should find the entity
        assert len(entities) == 1
        entity = entities[0]
        assert entity["name"] == "TestEntity"

        # Should report 2 matching observations
        assert entity["observationMatches"] == 2, \
            f"Expected 2 matching observations, got {entity['observationMatches']}"

        observations = entity["observations"]

        # All observations should be present
        assert len(observations) == 5

        # Matching observations should come first
        # The first two should contain "TARGET"
        assert "TARGET" in observations[0], f"First observation should match: {observations[0]}"
        assert "TARGET" in observations[1], f"Second observation should match: {observations[1]}"

        # Non-matching observations should come after
        assert "TARGET" not in observations[2], f"Third observation should not match: {observations[2]}"
        assert "TARGET" not in observations[3], f"Fourth observation should not match: {observations[3]}"
        assert "TARGET" not in observations[4], f"Fifth observation should not match: {observations[4]}"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()


def test_observation_sorting_with_many_observations(db):
    """Test with larger number of observations (simulating user's 135 observation case)."""

    async def run_test():
        # Create entity with many observations
        observations = []
        for i in range(50):
            if i % 10 == 0:
                # Every 10th observation matches
                observations.append(f"Observation {i} with MATCH keyword")
            else:
                observations.append(f"Observation {i} without keyword")

        await db.create_entities([
            {
                "name": "EntityWithMany",
                "entityType": "Test",
                "observations": observations
            }
        ])

        # Search for "MATCH"
        result = await db.search_nodes("MATCH")
        entities = result["entities"]

        assert len(entities) == 1
        entity = entities[0]

        # Should report 5 matching observations
        assert entity["observationMatches"] == 5, \
            f"Expected 5 matching observations, got {entity['observationMatches']}"

        returned_observations = entity["observations"]
        assert len(returned_observations) == 50

        # First 5 observations should all match (0, 10, 20, 30, 40)
        for i in range(5):
            assert "MATCH" in returned_observations[i], \
                f"Observation {i} should match, got: {returned_observations[i]}"

        # Remaining observations should not match (except we might have some that do)
        # Just verify that matching ones are clustered at the beginning
        matching_count = sum(1 for obs in returned_observations if "MATCH" in obs)
        assert matching_count == 5

        # Find index of last matching observation
        last_match_index = -1
        for i, obs in enumerate(returned_observations):
            if "MATCH" in obs:
                last_match_index = i

        # All matching observations should be in the first 5 positions
        assert last_match_index < 5, \
            f"Last matching observation at index {last_match_index}, should be < 5"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()

# Critical: create_relations MCP tool reports success but silently fails to persist relations

## Bug Description

The `create_relations` MCP tool consistently reports successful creation (returns `{"created": N, "relations": [...]}`) but relations are **not actually persisted** to the database. This is a silent failure causing severe graph health degradation.

## Evidence

Multiple calls to `create_relations` all reported success but relation count remained unchanged:

```text
Initial state: 98 entities, 49 relations (ratio: 0.50)

Call 1: create_relations with 20 relations
Response: {"created":20, "relations":[...]}
Actual: get_stats shows 49 relations (unchanged)

Call 2: create_relations with 3 relations
Response: {"created":3, "relations":[...]}
Actual: get_stats shows 49 relations (unchanged)
```

Database copy saved as `missing_rels.db` for debugging.

## Impact

1. **Silent failure** - No error returned, tool claims success
2. **Graph health degradation** - Ratio dropped to 0.50 (target: >2.0)
3. **Entity bias amplified** - Only entities persist, not relationships
4. **Corrupted graph** - Entities exist but lack critical connections
5. **Poor user experience** - Users trust success responses, don't verify

## Steps to Reproduce

1. Call `mcp_zabob-memgrap_create_relations` with any valid relations
2. Observe success response with `"created": N`
3. Call `mcp_zabob-memgrap_get_stats`
4. Note that `relation_count` has not increased

## Expected Behavior

- Relations should be persisted to database
- OR tool should return error if persistence fails
- Never claim success when operation didn't complete

## Actual Behavior

- Tool returns success message
- Relations are not written to database
- get_stats shows no change in relation_count
- No error or warning provided

## Context

This bug was discovered during conversation about entity bias in AI systems and knowledge graph health metrics. The irony: we were discussing why relations are underrepresented, and discovered the tool itself was silently dropping them!

## Related Code

Likely issue in:

- `memgraph/mcp_service.py` - `create_relations` tool implementation
- `memgraph/knowledge_live.py` - Relation persistence logic
- `memgraph/sqlite_backend.py` - SQLite transaction handling

## Suggested Fix

1. Add error handling for failed relation persistence
2. Add database commit verification
3. Return actual count from database after insert, not assumed count
4. Add logging for relation creation attempts vs successes
5. Consider transaction rollback if any relation in batch fails

## Test Case

```python
# Reproduce the issue
from memgraph.knowledge_live import DB

db = DB("test.db")

# Get initial count
initial_stats = db.get_stats()
initial_rels = initial_stats['relation_count']

# Try to create relations
result = db.create_relations([
    {"source": "Entity A", "target": "Entity B", "relation": "test_rel"}
])

# Check if actually created
final_stats = db.get_stats()
final_rels = final_stats['relation_count']

assert result['created'] == 1, "Tool claimed success"
assert final_rels == initial_rels + 1, f"Expected {initial_rels + 1}, got {final_rels}"
```

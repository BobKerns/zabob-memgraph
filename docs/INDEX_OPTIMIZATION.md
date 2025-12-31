![Zabob Memory Holodeck](images/zabob-banner.jpg)

# Index Optimization Analysis

## Query Pattern Analysis

Analyzed actual SQL queries in production code to optimize indexes.

### Most Frequent Queries

**1. Get observations for an entity (used in every graph read/search):**

```sql
SELECT content FROM observations
WHERE entity_id = ?
ORDER BY created_at
```

**2. Get relations for matched entities (used in search):**

```sql
SELECT * FROM relations
WHERE from_entity IN (...) OR to_entity IN (...)
```

**3. Lookup entity by name (used in create operations):**

```sql
SELECT id FROM entities WHERE name = ?
```

**4. Stats queries (rare, but important):**

```sql
SELECT COUNT(DISTINCT entity_type) FROM entities
SELECT COUNT(DISTINCT relation_type) FROM relations
```

## Index Optimizations

### ✅ Optimization 1: Compound Index for Observations

**Before:**

```sql
CREATE INDEX idx_observations_entity ON observations(entity_id);
CREATE INDEX idx_observations_created ON observations(created_at);
```

**After:**

```sql
-- Single compound index serves both WHERE and ORDER BY
CREATE INDEX idx_observations_entity_time ON observations(entity_id, created_at);
```

**Benefits:**

- ✅ Single index instead of two (less storage, faster writes)
- ✅ SQLite can use index for both filter AND sort in one pass
- ✅ No separate sort step needed (faster reads)

**Query Performance:**

```sql
-- Before: Uses idx_observations_entity, then separate sort
-- After: Uses idx_observations_entity_time for both filter and order
SELECT content FROM observations
WHERE entity_id = 42
ORDER BY created_at;
```

### ✅ Optimization 2: Remove Redundant Index

**Before:**

```sql
CREATE INDEX idx_entities_name ON entities (name);
-- Plus implicit index from: name TEXT UNIQUE NOT NULL
```

**After:**

```sql
-- Only the implicit index from UNIQUE constraint
-- No separate idx_entities_name needed
```

**Benefits:**

- ✅ Less storage (one index instead of two identical ones)
- ✅ Faster writes (only update one index)
- ✅ UNIQUE constraint index is sufficient for lookups

### ✅ Kept: Other Indexes

All other indexes serve active query patterns:

```sql
-- Used in stats queries
CREATE INDEX idx_entities_type ON entities(entity_type);

-- Used in WHERE from_entity IN (...)
CREATE INDEX idx_relations_from ON relations(from_entity);

-- Used in WHERE to_entity IN (...)
CREATE INDEX idx_relations_to ON relations(to_entity);

-- Used in stats and future relation type filtering
CREATE INDEX idx_relations_type ON relations(relation_type);
```

## Impact Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Observations indexes** | 2 | 1 | -50% |
| **Entities indexes** | 2 | 1 | -50% |
| **Total user indexes** | 7 | 5 | -29% |
| **Query performance** | Good | Better | Compound index optimizes hot path |
| **Write performance** | Good | Better | Fewer indexes to maintain |
| **Storage** | ~X bytes | ~0.85X bytes | Less index overhead |

## SQLite Query Planner Analysis

To verify indexes are being used optimally:

```sql
-- Should use idx_observations_entity_time for both WHERE and ORDER BY
EXPLAIN QUERY PLAN
SELECT content FROM observations
WHERE entity_id = 1
ORDER BY created_at;

-- Expected output:
-- SEARCH observations USING INDEX idx_observations_entity_time (entity_id=?)
```

Before optimization, this would show:

```sql
SEARCH observations USING INDEX idx_observations_entity (entity_id=?)
USE TEMP B-TREE FOR ORDER BY  -- Extra sort step!
```

## Testing

All tests pass with optimized indexes:

- ✅ test_new_schema.py - Schema creation and CRUD
- ✅ test_migration.py - Migration from v1 to v2
- ✅ test_ui_playwright.py - All 16 UI tests

## Future Considerations

### Vector Search (Future Enhancement)

When adding vector embeddings:

```sql
ALTER TABLE observations ADD COLUMN embedding BLOB;

-- Compound index would still be optimal:
-- (entity_id, created_at, embedding) if needed
-- Or use specialized vector index (HNSW, IVF)
```

### Observation Pagination (Future Enhancement)

Current compound index `(entity_id, created_at)` already optimal for:

```sql
SELECT content FROM observations
WHERE entity_id = ?
ORDER BY created_at
LIMIT 10 OFFSET 20;
```

### Covering Indexes (Considered but not implemented)

Could add observation content to index:

```sql
-- Covering index (not implemented)
CREATE INDEX idx_observations_covering
ON observations(entity_id, created_at, content);
```

**Decision: Not needed because:**

- SQLite's rowid-based storage is already efficient
- Observation content is variable length (index would be large)
- Current indexes + rowid lookups are fast enough
- Trade-off not worth the write overhead

## Migration Impact

The migration script creates optimized indexes from the start. No separate index migration needed.

**New databases:**

- Automatically get optimized indexes ✅

**Migrated databases:**

- Migration creates optimized indexes ✅
- Old indexes never existed (clean migration) ✅

## Recommendations

1. **Monitor query performance** in production
2. **Use EXPLAIN QUERY PLAN** if queries seem slow
3. **Consider VACUUM** after migration to reclaim space
4. **Keep indexes aligned** with actual query patterns

## References

- SQLite Index Documentation: https://www.sqlite.org/queryplanner.html
- Compound Index Benefits: https://www.sqlite.org/optoverview.html#covering_indexes
- Query Planner: https://www.sqlite.org/eqp.html

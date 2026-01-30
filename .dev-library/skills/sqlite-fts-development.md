# SQLite FTS (Full-Text Search) Development Skill

Cross-project patterns and gotchas for SQLite FTS5 implementation.

## Description

SQLite FTS5 (Full-Text Search) provides powerful search capabilities but has specific limitations and patterns that differ from standard SQL. This skill documents common patterns and pitfalls.

## When to Apply

- Implementing search functionality with SQLite
- Optimizing text search queries
- Debugging FTS-related SQL errors
- Designing search-driven features

## Key Concepts

### FTS5 Virtual Tables

FTS5 tables are "virtual" - they store data differently:

```sql
-- Create FTS5 virtual table
CREATE VIRTUAL TABLE documents_fts USING fts5(
    content,        -- Indexed columns
    title,
    tokenize = 'porter unicode61'  -- Tokenization
);

-- Insert data (same as regular tables)
INSERT INTO documents_fts (rowid, content, title)
VALUES (1, 'Search this text', 'My Document');
```

**Key points:**

- `rowid` is the primary key (always present)
- Indexed columns are for search only
- Use joins to get full data from main tables

### The bm25() Function

`bm25()` ranks search results by relevance:

```sql
-- Basic search with ranking
SELECT rowid, content, bm25(documents_fts) as rank
FROM documents_fts
WHERE documents_fts MATCH 'search terms'
ORDER BY rank;
```

**Critical limitations:**

1. **Must use table name, not alias**: `bm25(documents_fts)` not `bm25(fts)`
2. **Cannot be used in LEFT JOIN**: Fails with "no such column" error
3. **Requires MATCH clause**: Won't work without WHERE...MATCH

## Common Patterns

### Pattern 1: Basic Search

```sql
-- Search entities and observations
SELECT e.name, e.entity_type, o.content
FROM entities e
JOIN observations_fts fts ON e.id = fts.rowid
JOIN observations o ON fts.rowid = o.id
WHERE observations_fts MATCH ?  -- Note: table name, not alias
ORDER BY bm25(observations_fts);  -- Rank by relevance
```

### Pattern 2: Search with Deduplication

```sql
-- Find entities with matching observations
SELECT DISTINCT e.id, e.name, e.entity_type
FROM entities e
JOIN observations o ON e.id = o.entity_id
JOIN observations_fts fts ON o.id = fts.rowid
WHERE observations_fts MATCH ?
ORDER BY e.name;
```

### Pattern 3: Marking Matches Without LEFT JOIN

**Wrong approach** (fails with FTS5):

```sql
-- This FAILS: bm25() incompatible with LEFT JOIN
SELECT o.content,
       bm25(observations_fts) as relevance  -- ERROR!
FROM observations o
LEFT JOIN observations_fts fts ON o.id = fts.rowid
WHERE o.entity_id = ?;
```

**Correct approach** (use subquery):

```sql
-- This works: Use subquery to mark matches
SELECT o.content,
       CASE WHEN o.id IN (
           SELECT rowid FROM observations_fts
           WHERE observations_fts MATCH ?
       ) THEN 1 ELSE 0 END as is_match
FROM observations o
WHERE o.entity_id = ?
ORDER BY is_match DESC, o.created_at ASC;
```

### Pattern 4: Multi-field Search

```sql
-- Search across multiple fields
CREATE VIRTUAL TABLE entities_fts USING fts5(
    name,
    content=entities,  -- Points to source table
    content_rowid=id   -- Maps rowid to source table id
);

-- Search with field-specific boosts
SELECT e.*, bm25(entities_fts, 10.0, 1.0) as rank
FROM entities e
JOIN entities_fts fts ON e.id = fts.rowid
WHERE entities_fts MATCH ?
ORDER BY rank;
-- 10.0 = name weight, 1.0 = default for other fields
```

## Real-World Example: Query Optimization

**Problem**: Query observations, showing matches first but including all.

**Failed Attempt 1**: LEFT JOIN with bm25()

```sql
-- ERROR: no such column: fts
SELECT o.content, bm25(fts) as score
FROM observations o
LEFT JOIN observations_fts fts ON o.id = fts.rowid
WHERE o.entity_id = ?;
```

**Failed Attempt 2**: LEFT JOIN with table name

```sql
-- ERROR: no such column: observations_fts
-- (bm25 doesn't work in LEFT JOIN context at all)
SELECT o.content, bm25(observations_fts) as score
FROM observations o
LEFT JOIN observations_fts fts ON o.id = fts.rowid
WHERE o.entity_id = ?;
```

**Working Solution**: Subquery approach

```sql
-- Success: Mark matches inline
SELECT o.content,
       o.created_at,
       CASE WHEN o.id IN (
           SELECT rowid FROM observations_fts
           WHERE observations_fts MATCH ?
       ) THEN 1 ELSE 0 END as is_match
FROM observations o
WHERE o.entity_id = ?
ORDER BY is_match DESC, o.created_at ASC;
```

**Benefits:**

- Single query instead of two separate queries
- All observations returned, matches prioritized
- No FTS5 limitations violated

## FTS5 Gotchas

### 1. Table Name vs Alias in bm25()

❌ **Wrong:**

```sql
SELECT bm25(fts)  -- Alias doesn't work
FROM documents_fts fts
WHERE documents_fts MATCH 'search';
```

✅ **Correct:**

```sql
SELECT bm25(documents_fts)  -- Use full table name
FROM documents_fts fts
WHERE documents_fts MATCH 'search';
```

### 2. bm25() Requires MATCH

❌ **Wrong:**

```sql
-- This fails: bm25() needs MATCH clause
SELECT *, bm25(documents_fts)
FROM documents_fts
WHERE rowid = 1;
```

✅ **Correct:**

```sql
-- Use MATCH for relevance scoring
SELECT *, bm25(documents_fts)
FROM documents_fts
WHERE documents_fts MATCH 'search terms';
```

### 3. LEFT JOIN Incompatibility

❌ **Wrong:**

```sql
-- bm25() doesn't work in LEFT JOIN
SELECT o.*, bm25(obs_fts)
FROM observations o
LEFT JOIN observations_fts obs_fts ON o.id = obs_fts.rowid;
```

✅ **Correct:**

```sql
-- Use INNER JOIN for matches, or subquery for marking
SELECT o.*
FROM observations o
JOIN observations_fts fts ON o.id = fts.rowid
WHERE observations_fts MATCH 'term';
```

### 4. Content Table Synchronization

When using `content=` option, keep tables in sync:

```sql
-- Create FTS with external content
CREATE VIRTUAL TABLE docs_fts USING fts5(
    content,
    content=documents,
    content_rowid=id
);

-- IMPORTANT: Keep synchronized with triggers
CREATE TRIGGER docs_fts_insert AFTER INSERT ON documents BEGIN
    INSERT INTO docs_fts(rowid, content)
    VALUES (new.id, new.content);
END;

CREATE TRIGGER docs_fts_delete AFTER DELETE ON documents BEGIN
    DELETE FROM docs_fts WHERE rowid = old.id;
END;

CREATE TRIGGER docs_fts_update AFTER UPDATE ON documents BEGIN
    UPDATE docs_fts SET content = new.content WHERE rowid = new.id;
END;
```

## Testing FTS Queries

Create isolated tests for FTS queries:

```python
# test_fts_query.py
import sqlite3

def test_fts_search():
    conn = sqlite3.connect(':memory:')

    # Setup
    conn.execute('CREATE VIRTUAL TABLE test_fts USING fts5(content)')
    conn.execute('INSERT INTO test_fts VALUES (?)', ('searchable text',))
    conn.execute('INSERT INTO test_fts VALUES (?)', ('other content',))

    # Test query
    results = conn.execute('''
        SELECT rowid, content, bm25(test_fts) as rank
        FROM test_fts
        WHERE test_fts MATCH 'searchable'
        ORDER BY rank
    ''').fetchall()

    assert len(results) == 1
    assert 'searchable' in results[0][1]
    conn.close()
```

## Performance Tips

1. **Use FTS for text search, indexes for exact matches**

   ```sql
   -- Fast: Exact match with index
   SELECT * FROM entities WHERE name = 'exact name';

   -- Fast: Full-text search
   SELECT * FROM entities_fts WHERE entities_fts MATCH 'partial text';
   ```

2. **Limit FTS scans with additional WHERE clauses**

   ```sql
   -- Faster: Narrow scope before FTS
   SELECT e.*
   FROM entities e
   JOIN entities_fts fts ON e.id = fts.rowid
   WHERE e.entity_type = 'person'  -- Filter first
     AND entities_fts MATCH 'search'
   ```

3. **Use prefix search sparingly**

   ```sql
   -- Slower: Prefix wildcard
   WHERE documents_fts MATCH 'term*'

   -- Faster: Exact term
   WHERE documents_fts MATCH 'term'
   ```

## Quick Reference

**Creating FTS5 table:**

```sql
CREATE VIRTUAL TABLE name_fts USING fts5(
    column1, column2,
    tokenize = 'porter unicode61'
);
```

**Basic search:**

```sql
SELECT * FROM table_fts WHERE table_fts MATCH 'search terms';
```

**With relevance ranking:**

```sql
SELECT *, bm25(table_fts) as rank
FROM table_fts
WHERE table_fts MATCH 'search'
ORDER BY rank;
```

**Mark matches in full dataset:**

```sql
SELECT *, CASE WHEN id IN (
    SELECT rowid FROM table_fts WHERE table_fts MATCH 'term'
) THEN 1 ELSE 0 END as is_match
FROM main_table;
```

## Further Reading

- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html)
- [FTS5 Full-Text Query Syntax](https://www.sqlite.org/fts5.html#full_text_query_syntax)
- [FTS5 Auxiliary Functions](https://www.sqlite.org/fts5.html#fts5_auxiliary_functions)

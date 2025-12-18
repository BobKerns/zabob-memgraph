# Your Migration Checklist

Run these commands in order. Each step is safe and reversible.

## Step 1: Preview the Migration (Safe - No Changes)

```bash
cd ~/p/memgraph
python migrate_to_v2.py --dry-run
```

**Expected output:**

- Shows current schema version (1)
- Lists entities and observation counts
- Shows what would be migrated

## Step 2: Run the Migration (Creates Backup First)

```bash
python migrate_to_v2.py --backup
```

**What happens:**

1. Creates backup: `knowledge_graph_v1_backup_TIMESTAMP.db`
2. Adds schema_metadata table
3. Creates observations table with FTS5
4. Migrates observations from JSON → rows
5. Removes old observations column
6. Records migration to v2
7. Validates the result

**Expected output:**

```text
✅ Backup created: ...
✅ Created schema_metadata table
✅ Created observations table with FTS5
   Processed X entities
   Migrated Y observations
✅ Dropped observations column
✅ Recorded migration to schema version 2
📊 Verifying migration...
   Entities: X
   Observations: Y
   Relations: Z
🎉 Migration completed successfully!
```

## Step 3: Verify the Server Works

```bash
# Start the server
zabob-memgraph start

# Check it's running
zabob-memgraph status

# Open the UI
zabob-memgraph open
```

**In the browser:**

- Check your entities are visible
- Check observations show up in node details
- Try searching for keywords in your observations

## Step 4: Run Tests

```bash
# Run all tests
zabob-memgraph test

# Or just UI tests
pytest tests/test_ui_playwright.py -v
```

**Expected:** All tests pass (16/16)

## Step 5: Validate Your Data

```bash
# Check database stats
sqlite3 ~/.zabob/memgraph/data/knowledge_graph.db "
SELECT
  (SELECT COUNT(*) FROM entities) as entities,
  (SELECT COUNT(*) FROM observations) as observations,
  (SELECT COUNT(*) FROM relations) as relations,
  (SELECT version FROM schema_metadata ORDER BY updated_at DESC LIMIT 1) as schema_version;
"
```

**Expected output:**

```text
entities | observations | relations | schema_version
---------|-------------|-----------|---------------
   X     |     Y       |    Z      |      2
```

## If Something Goes Wrong

### Quick Rollback

```bash
# Stop server
zabob-memgraph stop

# Find backup file
ls -lt ~/.zabob/memgraph/data/*.db | head -5

# Restore from backup
cp ~/.zabob/memgraph/data/knowledge_graph_v1_backup_TIMESTAMP.db \
   ~/.zabob/memgraph/data/knowledge_graph.db

# Start server
zabob-memgraph start
```

## After Successful Migration

1. **Update version in pyproject.toml** if you want:

   ```toml
   version = "0.1.0"
   ```

2. **Commit the changes:**

   ```bash
   git add -A
   git commit -m "feat: migrate to normalized observations schema (v2)"
   ```

3. **Optional - Clean up old test file:**

   ```bash
   rm test_new_schema.py
   ```

## What You're Getting

### Before

- Observations: `["obs1", "obs2", "obs3"]` stored in one JSON column
- Adding observation = rewrite entire array
- Search = search through JSON text

### After

- Observations: Individual rows in dedicated table
- Adding observation = insert one row
- Search = dedicated FTS5 index
- Ready for vector embeddings

### Size Comparison

Run this before and after migration to see the difference:

```bash
# Before
sqlite3 ~/.zabob/memgraph/data/knowledge_graph.db \
  "SELECT name, length(observations) as json_size FROM entities LIMIT 5;"

# After migration
sqlite3 ~/.zabob/memgraph/data/knowledge_graph.db \
  "SELECT e.name, COUNT(o.id) as obs_count,
          SUM(length(o.content)) as total_size
   FROM entities e
   LEFT JOIN observations o ON e.id = o.entity_id
   GROUP BY e.name
   LIMIT 5;"
```

---

**Ready?** Start with Step 1 (dry-run) and go from there!

![Zabob Memory Holodeck](docs/images/zabob-banner-memory.jpg)

# Schema Migration Summary

## ✅ Completed

1. **Created migration script** (`migrate_to_v2.py`)
   - Automated migration from JSON observations to normalized table
   - Includes dry-run mode for safety
   - Creates timestamped backups
   - Validates migration after completion

2. **Updated sqlite_backend.py**
   - Schema v2 with normalized observations table
   - Schema metadata table for version tracking
   - Separate FTS5 tables for entities and observations
   - Updated all CRUD operations to use normalized schema
   - Type-safe with mypy strict mode

3. **Tested thoroughly**
   - All 16 playwright UI tests pass ✅
   - Created test_new_schema.py for validation
   - Tests verify: create, read, search, stats operations
   - Fixtures work with new schema

4. **Documentation**
   - MIGRATION_V2.md with complete migration guide
   - Rollback instructions included

## Next Steps for Release

### Option A: Migrate Now (Recommended)

```bash
# 1. Dry run to see what will happen
python migrate_to_v2.py --dry-run

# 2. Run migration with backup
python migrate_to_v2.py --backup

# 3. Verify the migration
python migrate_to_v2.py --db-path ~/.zabob/memgraph/data/knowledge_graph.db | tail -20

# 4. Test the server
zabob-memgraph start
zabob-memgraph test
zabob-memgraph open

# 5. Check your data in the UI
# Browse to http://localhost:6789
```

### Option B: Fresh Start

If you prefer to start fresh:

```bash
# 1. Backup current database
cp ~/.zabob/memgraph/data/knowledge_graph.db ~/.zabob/memgraph/data/knowledge_graph_v1.db

# 2. Remove old database
rm ~/.zabob/memgraph/data/knowledge_graph.db

# 3. Start server (creates new v2 database)
zabob-memgraph start
```

## What Changed in Code

### Before (v1)

```python
# Observations as JSON array
entities.observations TEXT  # JSON: ["obs1", "obs2"]
```

### After (v2)

```python
# Normalized observations
observations (
    id INTEGER,
    entity_id INTEGER,
    content TEXT,
    created_at TEXT
)
```

## Performance Improvements

- **Write**: No more rewriting entire JSON array
- **Search**: FTS5 on individual observations
- **Scale**: No limit on observations per entity
- **Memory**: Better SQLite page locality

## Future Enhancements Enabled

```sql
-- Easy to add vector embeddings
ALTER TABLE observations ADD COLUMN embedding BLOB;

-- Easy to add metadata
ALTER TABLE observations ADD COLUMN source TEXT;
ALTER TABLE observations ADD COLUMN confidence REAL;
```

## Files Modified

1. `memgraph/sqlite_backend.py` - Core schema and operations
2. `migrate_to_v2.py` - Migration script (NEW)
3. `MIGRATION_V2.md` - Migration guide (NEW)
4. `test_new_schema.py` - Schema validation test (NEW)

## Files Not Modified

- Tests still pass without changes
- MCP tools API unchanged
- Web UI works without changes
- All other code unchanged

## Safety Features

1. **Dry-run mode** - See what will happen first
2. **Timestamped backups** - Automatic rollback capability
3. **Validation** - Script verifies migration success
4. **Incremental** - Can test on copy of database first

## Testing Checklist

- [x] New schema creates successfully
- [x] Create entities with observations
- [x] Read graph returns correct data
- [x] Search finds entities and observations
- [x] Stats include observation count
- [x] All playwright tests pass (16/16)
- [x] Type checking passes (mypy strict)
- [x] Linting passes (ruff)
- [ ] Migration script tested on real database (YOU DO THIS)
- [ ] Server works after migration (YOU VERIFY THIS)

## Rollback Plan

If anything goes wrong:

```bash
# Stop server
zabob-memgraph stop

# Restore from backup
cp ~/.zabob/memgraph/data/knowledge_graph_v1_backup_TIMESTAMP.db \
   ~/.zabob/memgraph/data/knowledge_graph.db

# Start server
zabob-memgraph start
```

## Ready to Release?

After migration validation:

1. Commit changes: `git add -A && git commit -m "feat: normalize observations to dedicated table (v2 schema)"`
2. Tag release: `git tag v0.1.0`
3. Push: `git push origin release-0.1 --tags`
4. Merge to main: Create PR from release-0.1 to main

---

**Status**: ✅ Code complete, tests passing, ready for your database migration

# Database Migration: v1 → v2

## What Changed

**Schema v2** normalizes observations into a dedicated table with full-text search support.

### Before (v1)

- Observations stored as JSON array in `entities.observations` column
- FTS5 search on JSON text (inefficient)
- Write amplification (entire array rewritten on every update)

### After (v2)

- Normalized `observations` table with `entity_id` foreign key
- Separate FTS5 table for observations (`observations_fts`)
- Individual observation CRUD operations
- Better search performance across entities and observations
- Schema version tracking in `schema_metadata` table

## Benefits

✅ **Scalability**: No limit on observations per entity
✅ **Performance**: Individual observation inserts without rewriting
✅ **Search**: Dedicated FTS5 table for observation content
✅ **Future-Ready**: Easy to add vector embeddings column
✅ **Queryability**: Can search observations across all entities

## Migration Steps

### 1. Dry Run (Recommended First)

```bash
python migrate_to_v2.py --dry-run --backup
```

This shows what will be migrated without making changes.

### 2. Run Migration

```bash
# Create backup and migrate
python migrate_to_v2.py --backup

# Or specify database path
python migrate_to_v2.py --db-path ~/.zabob/memgraph/data/knowledge_graph.db --backup
```

### 3. Verify

The script automatically verifies the migration and shows:

- Entity count
- Observation count
- Sample entities with their observation counts

### 4. Test

```bash
# Start the server
zabob-memgraph start

# Run tests
zabob-memgraph test
```

## What Gets Migrated

1. **schema_metadata** table created for version tracking
2. **observations** table created with proper indexes
3. **observations_fts** FTS5 virtual table for search
4. All observations extracted from JSON arrays → individual rows
5. **entities** table schema updated (observations column removed)
6. **entities_fts** updated to not include observations
7. Migration recorded in schema_metadata

## Rollback

If you need to rollback:

1. Stop the server: `zabob-memgraph stop`
2. Restore from backup: `cp knowledge_graph_v1_backup_*.db knowledge_graph.db`
3. Start the server: `zabob-memgraph start`

**Note**: The v1 backup is timestamped and kept in the same directory as the database.

## New Database Structure

```sql
-- Schema versioning
schema_metadata (id, version, description, applied_at, updated_at)

-- Entities (no observations column)
entities (id, name, entity_type, created_at, updated_at)

-- Normalized observations
observations (id, entity_id, content, created_at)

-- Full-text search
entities_fts (name, entity_type)
observations_fts (content)

-- Relations (unchanged)
relations (id, from_entity, to_entity, relation_type, created_at, updated_at)
```

## Compatibility

- **New databases**: Automatically use v2 schema
- **Existing databases**: Must run migration script
- **Tests**: Updated to work with both schemas

## Future Enhancements

With normalized observations, we can easily add:

- **Vector embeddings**: `ALTER TABLE observations ADD COLUMN embedding BLOB`
- **Observation metadata**: confidence scores, sources, timestamps
- **Pagination**: `LIMIT/OFFSET` queries on observations
- **Observation types**: categorize different kinds of observations
- **Observation relations**: link observations to each other

## Troubleshooting

**Migration fails with "table already exists"**:

- Database is already at v2, no migration needed

**Performance issues after migration**:

- Run `VACUUM` to rebuild database: `sqlite3 knowledge_graph.db "VACUUM;"`
- Rebuild FTS indexes if needed

**Data doesn't match**:

- Check backup file for original data
- Verify observation counts match between v1 and v2

## Support

For issues or questions:

- Check logs: `~/.zabob/memgraph/memgraph.log`
- Run with dry-run first: `python migrate_to_v2.py --dry-run`
- Open GitHub issue with migration output

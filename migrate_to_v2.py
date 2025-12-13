#!/usr/bin/env python3
"""
Database Migration Script: v1 → v2

Migrates from JSON array observations to normalized observations table.
Adds database metadata table for version tracking.

Usage:
    python migrate_to_v2.py [--db-path PATH] [--backup] [--dry-run]
"""

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, UTC
from pathlib import Path


SCHEMA_VERSION = 2


def backup_database(db_path: Path) -> Path:
    """Create a timestamped backup of the database"""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_v1_backup_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from metadata table"""
    try:
        cursor = conn.execute("SELECT version FROM schema_metadata ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 1
    except sqlite3.OperationalError:
        # Table doesn't exist, assume v1
        return 1


def create_metadata_table(conn: sqlite3.Connection) -> None:
    """Create schema_metadata table for version tracking"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )
    print("✅ Created schema_metadata table")


def create_observations_table(conn: sqlite3.Connection) -> None:
    """Create normalized observations table with FTS5"""
    conn.executescript(
        """
        -- Main observations table
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
        );

        -- Compound index for entity_id + created_at (supports WHERE and ORDER BY)
        CREATE INDEX IF NOT EXISTS idx_observations_entity_time ON observations(entity_id, created_at);

        -- Full-text search for observations
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
            content,
            content='observations',
            content_rowid='id'
        );

        -- Triggers to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS observations_fts_insert AFTER INSERT ON observations BEGIN
            INSERT INTO observations_fts(rowid, content)
            VALUES (new.id, new.content);
        END;

        CREATE TRIGGER IF NOT EXISTS observations_fts_delete AFTER DELETE ON observations BEGIN
            DELETE FROM observations_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS observations_fts_update AFTER UPDATE ON observations BEGIN
            DELETE FROM observations_fts WHERE rowid = old.id;
            INSERT INTO observations_fts(rowid, content)
            VALUES (new.id, new.content);
        END;
    """
    )
    print("✅ Created observations table with FTS5")


def migrate_observations_data(conn: sqlite3.Connection, dry_run: bool = False) -> dict[str, int]:
    """Migrate observations from JSON arrays to normalized table"""
    stats = {"entities_processed": 0, "observations_migrated": 0}

    # Get all entities with their observations and timestamps
    cursor = conn.execute("SELECT id, name, observations, updated_at FROM entities")
    entities = cursor.fetchall()

    for entity_id, entity_name, observations_json, entity_updated_at in entities:
        try:
            observations = json.loads(observations_json)
            stats["entities_processed"] += 1

            if not dry_run:
                # Use entity's updated_at timestamp - observations can't be newer than the entity
                for obs_content in observations:
                    conn.execute(
                        """
                        INSERT INTO observations (entity_id, content, created_at)
                        VALUES (?, ?, ?)
                    """,
                        (entity_id, obs_content, entity_updated_at),
                    )
                    stats["observations_migrated"] += 1
            else:
                stats["observations_migrated"] += len(observations)

            if dry_run:
                print(f"  Would migrate {len(observations)} observations from '{entity_name}'")

        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Failed to parse observations for entity {entity_name}: {e}")

    return stats


def drop_old_observations_column(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Remove the old observations column from entities table"""
    if dry_run:
        print("  Would drop 'observations' column from entities table")
        return

    # SQLite doesn't support DROP COLUMN directly (before 3.35.0), so we recreate the table
    conn.executescript(
        """
        -- Create new entities table without observations column
        CREATE TABLE entities_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Copy data from old table
        INSERT INTO entities_new (id, name, entity_type, created_at, updated_at)
        SELECT id, name, entity_type, created_at, updated_at FROM entities;

        -- Drop old table and rename new one
        DROP TABLE entities;
        ALTER TABLE entities_new RENAME TO entities;

        -- Recreate indexes
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (name);
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type);

        -- Update entities FTS to not include observations
        DROP TRIGGER IF EXISTS entities_fts_insert;
        DROP TRIGGER IF EXISTS entities_fts_delete;
        DROP TRIGGER IF EXISTS entities_fts_update;
        DROP TABLE IF EXISTS entities_fts;

        CREATE VIRTUAL TABLE entities_fts USING fts5(
            name, entity_type, content='entities'
        );

        CREATE TRIGGER entities_fts_insert AFTER INSERT ON entities BEGIN
            INSERT INTO entities_fts(rowid, name, entity_type)
            VALUES (new.id, new.name, new.entity_type);
        END;

        CREATE TRIGGER entities_fts_delete AFTER DELETE ON entities BEGIN
            DELETE FROM entities_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER entities_fts_update AFTER UPDATE ON entities BEGIN
            DELETE FROM entities_fts WHERE rowid = old.id;
            INSERT INTO entities_fts(rowid, name, entity_type)
            VALUES (new.id, new.name, new.entity_type);
        END;
    """
    )
    print("✅ Dropped observations column and updated entities FTS")


def record_migration(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Record the migration in schema_metadata"""
    if dry_run:
        print("  Would record migration to schema v2")
        return

    timestamp = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO schema_metadata (version, description, applied_at, updated_at)
        VALUES (?, ?, ?, ?)
    """,
        (
            SCHEMA_VERSION,
            "Normalized observations table with FTS5, removed JSON array column",
            timestamp,
            timestamp,
        ),
    )
    print(f"✅ Recorded migration to schema version {SCHEMA_VERSION}")


def verify_migration(conn: sqlite3.Connection) -> bool:
    """Verify the migration was successful"""
    print("\n📊 Verifying migration...")

    # Check entities count
    cursor = conn.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]
    print(f"  Entities: {entity_count}")

    # Check observations count
    cursor = conn.execute("SELECT COUNT(*) FROM observations")
    obs_count = cursor.fetchone()[0]
    print(f"  Observations: {obs_count}")

    # Check relations count
    cursor = conn.execute("SELECT COUNT(*) FROM relations")
    rel_count = cursor.fetchone()[0]
    print(f"  Relations: {rel_count}")

    # Sample a few entities to verify observations
    cursor = conn.execute(
        """
        SELECT e.name, COUNT(o.id) as obs_count
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        GROUP BY e.id, e.name
        LIMIT 5
    """
    )

    print("\n  Sample entities:")
    for name, obs_count in cursor:
        print(f"    - {name}: {obs_count} observations")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate database from v1 to v2 schema")
    parser.add_argument("--db-path", type=Path, help="Path to database file (default: knowledge_graph.db)")
    parser.add_argument("--backup", action="store_true", help="Create backup before migration (recommended)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    # Determine database path
    if args.db_path:
        db_path = args.db_path
    else:
        # Use same logic as sqlite_backend.py
        import os

        db_path = Path(os.getenv("MEMGRAPH_DATABASE_PATH", "knowledge_graph.db"))
        if not db_path.is_absolute():
            base_dir = Path(__file__).parent
            db_path = base_dir / db_path

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print("🔧 Database Migration: v1 → v2")
    print(f"   Database: {db_path.absolute()}")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    # Create backup if requested
    if args.backup and not args.dry_run:
        backup_database(db_path)

    # Open database connection
    with sqlite3.connect(db_path) as conn:
        # Check current version
        current_version = get_current_version(conn)
        print(f"📌 Current schema version: {current_version}")

        if current_version >= SCHEMA_VERSION:
            print(f"✅ Database is already at version {current_version}, no migration needed")
            return

        # Step 1: Create metadata table
        print("\n1️⃣  Creating schema_metadata table...")
        if not args.dry_run:
            create_metadata_table(conn)

        # Step 2: Create new observations table
        print("\n2️⃣  Creating normalized observations table...")
        if not args.dry_run:
            create_observations_table(conn)

        # Step 3: Migrate data
        print("\n3️⃣  Migrating observations data...")
        stats = migrate_observations_data(conn, dry_run=args.dry_run)
        print(f"   Processed {stats['entities_processed']} entities")
        print(f"   Migrated {stats['observations_migrated']} observations")

        # Step 4: Drop old column
        print("\n4️⃣  Removing old observations column...")
        drop_old_observations_column(conn, dry_run=args.dry_run)

        # Step 5: Record migration
        print("\n5️⃣  Recording migration...")
        record_migration(conn, dry_run=args.dry_run)

        # Commit changes
        if not args.dry_run:
            conn.commit()
            print("\n✅ Migration committed")

            # Verify
            if verify_migration(conn):
                print("\n🎉 Migration completed successfully!")
        else:
            print("\n✅ Dry run completed (no changes made)")


if __name__ == "__main__":
    main()

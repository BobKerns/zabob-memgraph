"""
SQLite Database Backend for Knowledge Graph

This module provides a SQLite-based storage backend for the knowledge graph,
with import functionality from MCP data sources.
"""

import asyncio
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from memgraph.config import Config
from memgraph.backup import backup_database


@dataclass
class EntityRecord:
    id: int | None
    name: str
    entity_type: str
    observations: list[str]
    created_at: str
    updated_at: str


@dataclass
class RelationRecord:
    id: int | None
    from_entity: str
    to_entity: str
    relation_type: str
    created_at: str
    updated_at: str


class SQLiteKnowledgeGraphDB:
    """
    SQLite-based knowledge graph database with MCP import functionality.
    """

    _lock: asyncio.Lock
    db_path: Path
    """Location of the SQLite database file"""
    min_backups: int
    """Minimum number of backups to keep"""
    min_age: int
    """Minimum age of backups to keep in days"""
    backup_on_start: bool
    """Whether to perform a backup on startup"""

    def __init__(
        self,
        config: Config | None = None,
        db_path: str | Path | None = None,
        min_backups: int = 5,
        min_age: int = 7,
        backup_on_start: bool = True,
    ) -> None:
        self._lock = asyncio.Lock()
        if config:
            db_path = config.get("database_path", db_path)
            min_backups = config.get("min_backups", min_backups)
            min_age = config.get("backup_age_days", min_age)
            backup_on_start = config.get("backup_on_start", backup_on_start)

        # Get database path from environment or parameter
        if db_path is None:
            config_dir = Path.home() / ".zabob" / "memgraph"
            db_path = config_dir / "data" / "knowledge_graph.db"
            db_path = Path(os.getenv("MEMGRAPH_DATABASE_PATH", str(db_path)))
            if not db_path.is_absolute():
                raise ValueError("MEMGRAPH_DATABASE_PATH must be an absolute path")

        # If the user provided a relative path, it's relative to current working directory
        # Resolve it now.
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.min_backups = min_backups
        self.min_age = min_age
        self.backup_on_start = backup_on_start

        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema"""
        if self.backup_on_start:
            self.backup_database()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                -- Schema metadata for versioning
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Entities table (no observations column)
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    entity_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Normalized observations table
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_entity TEXT NOT NULL,
                    to_entity TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (from_entity) REFERENCES entities (name),
                    FOREIGN KEY (to_entity) REFERENCES entities (name),
                    UNIQUE(from_entity, to_entity, relation_type)
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type);
                -- Compound index for observations: supports both WHERE entity_id and ORDER BY created_at
                CREATE INDEX IF NOT EXISTS idx_observations_entity_time ON observations(entity_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_relations_from ON relations (from_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_to ON relations (to_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_type ON relations (relation_type);

                -- Full-text search for entities
                CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                    name, entity_type, content='entities'
                );

                -- Full-text search for observations
                CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
                    content, content='observations', content_rowid='id'
                );

                -- Triggers to keep entities FTS in sync
                CREATE TRIGGER IF NOT EXISTS entities_fts_insert AFTER INSERT ON entities BEGIN
                    INSERT INTO entities_fts(rowid, name, entity_type)
                    VALUES (new.id, new.name, new.entity_type);
                END;

                CREATE TRIGGER IF NOT EXISTS entities_fts_delete AFTER DELETE ON entities BEGIN
                    DELETE FROM entities_fts WHERE rowid = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS entities_fts_update AFTER UPDATE ON entities BEGIN
                    DELETE FROM entities_fts WHERE rowid = old.id;
                    INSERT INTO entities_fts(rowid, name, entity_type)
                    VALUES (new.id, new.name, new.entity_type);
                END;

                -- Triggers to keep observations FTS in sync
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
            self._ensure_schema_version(conn)

    def backup_database(self) -> None:
        """Create a backup of the database"""
        backup_database(
            self.db_path,
            min_backups=self.min_backups,
            min_age=self.min_age,
        )

    def _ensure_schema_version(self, conn: sqlite3.Connection) -> None:
        """Ensure schema is at the correct version"""
        try:
            cursor = conn.execute("SELECT version FROM schema_metadata ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row[0] >= 2:
                return  # Schema is up to date
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet

        # Record schema version for new databases
        timestamp = datetime.now(UTC).isoformat()
        conn.execute(
            """
            INSERT INTO schema_metadata (version, description, applied_at, updated_at)
            VALUES (?, ?, ?, ?)
        """,
            (2, "Initial schema with normalized observations", timestamp, timestamp),
        )
        conn.commit()

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph from SQLite"""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row

                    # Get all entities with their observations
                    entities_cursor = conn.execute(
                        """
                        SELECT e.id, e.name, e.entity_type
                        FROM entities e
                        ORDER BY e.name
                    """
                    )

                    entities = []
                    for row in entities_cursor:
                        entity_id = row["id"]
                        # Get observations for this entity
                        obs_cursor = conn.execute(
                            "SELECT content FROM observations WHERE entity_id = ? ORDER BY created_at",
                            (entity_id,),
                        )
                        observations = [obs_row["content"] for obs_row in obs_cursor]

                        entities.append(
                            {
                                "name": row["name"],
                                "entityType": row["entity_type"],
                                "observations": observations,
                            }
                        )

                    # Get all relations
                    relations_cursor = conn.execute(
                        """
                        SELECT from_entity, to_entity, relation_type
                        FROM relations
                        ORDER BY from_entity, to_entity
                    """
                    )

                    relations = []
                    for row in relations_cursor:
                        relations.append(
                            {
                                "from_entity": row["from_entity"],
                                "to": row["to_entity"],
                                "relationType": row["relation_type"],
                            }
                        )

                    return {"entities": entities, "relations": relations}

            except Exception as e:
                print(f"SQLite read_graph failed: {e}")
                return {"entities": [], "relations": []}

    async def search_nodes(self, query: str) -> dict[str, Any]:
        """Search nodes using SQLite FTS with OR logic and BM25 ranking"""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row

                    # Transform query to use OR logic: split terms and join with OR
                    # This allows partial matches instead of requiring all terms
                    terms = query.strip().split()
                    if not terms:
                        return {"entities": [], "relations": []}

                    # Create OR query from terms
                    or_query = " OR ".join(terms)

                    # Search in both entities and observations FTS with ranking
                    # Using dict to store (entity_id, score) pairs, keeping best score
                    entity_scores: dict[int, float] = {}

                    # Search entities with BM25 ranking
                    entity_search = conn.execute(
                        """
                        SELECT e.id, bm25(entities_fts) as score
                        FROM entities e
                        JOIN entities_fts fts ON e.id = fts.rowid
                        WHERE entities_fts MATCH ?
                    """,
                        (or_query,),
                    )
                    for row in entity_search:
                        entity_id = row["id"]
                        score = row["score"]
                        # BM25 returns negative scores (closer to 0 is better)
                        # Keep the best (highest/closest to 0) score
                        if entity_id not in entity_scores or score > entity_scores[entity_id]:
                            entity_scores[entity_id] = score

                    # Search observations with BM25 ranking
                    obs_search = conn.execute(
                        """
                        SELECT o.entity_id, bm25(observations_fts) as score
                        FROM observations o
                        JOIN observations_fts fts ON o.id = fts.rowid
                        WHERE observations_fts MATCH ?
                    """,
                        (or_query,),
                    )
                    for row in obs_search:
                        entity_id = row["entity_id"]
                        score = row["score"]
                        # Keep the best score for this entity
                        if entity_id not in entity_scores or score > entity_scores[entity_id]:
                            entity_scores[entity_id] = score

                    # Sort entity IDs by score (best first)
                    entity_ids = sorted(entity_scores.keys(), key=lambda eid: entity_scores[eid], reverse=True)

                    # Get full entity data for matches (in ranked order)
                    entities = []
                    entity_names = set()

                    if entity_ids:
                        placeholders = ",".join("?" * len(entity_ids))
                        # Use CASE to preserve the ranking order
                        order_cases = " ".join([
                            f"WHEN e.id = ? THEN {i}"
                            for i in range(len(entity_ids))
                        ])
                        entities_cursor = conn.execute(
                            f"""
                            SELECT e.id, e.name, e.entity_type
                            FROM entities e
                            WHERE e.id IN ({placeholders})
                            ORDER BY CASE {order_cases} END
                        """,
                            list(entity_ids) + list(entity_ids),  # IDs for IN clause + IDs for CASE
                        )

                        for row in entities_cursor:
                            entity_id = row["id"]
                            entity_name = row["name"]

                            # Get observations
                            obs_cursor = conn.execute(
                                "SELECT content FROM observations WHERE entity_id = ? ORDER BY created_at",
                                (entity_id,),
                            )
                            observations = [obs_row["content"] for obs_row in obs_cursor]

                            entities.append(
                                {
                                    "name": entity_name,
                                    "entityType": row["entity_type"],
                                    "observations": observations,
                                }
                            )
                            entity_names.add(entity_name)

                    # Get relations for matching entities
                    if entity_names:
                        placeholders = ",".join("?" * len(entity_names))
                        relations_cursor = conn.execute(
                            f"""
                            SELECT from_entity, to_entity, relation_type
                            FROM relations
                            WHERE from_entity IN ({placeholders})
                               OR to_entity IN ({placeholders})
                        """,
                            list(entity_names) + list(entity_names),
                        )

                        relations = []
                        for row in relations_cursor:
                            relations.append(
                                {
                                    "from_entity": row["from_entity"],
                                    "to": row["to_entity"],
                                    "relationType": row["relation_type"],
                                }
                            )
                    else:
                        relations = []

                    return {"entities": entities, "relations": relations}

            except Exception as e:
                print(f"SQLite search_nodes failed: {e}")
                # Fallback to simple LIKE search
                return await self._simple_search(query)

    async def _simple_search(self, query: str) -> dict[str, Any]:
        """Simple LIKE-based search fallback"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Simple search in name, entity_type, and observation content
                entity_ids: set[int] = set()

                # Search entities by name and type
                entity_search = conn.execute(
                    """
                    SELECT id FROM entities
                    WHERE name LIKE ? OR entity_type LIKE ?
                """,
                    (f"%{query}%", f"%{query}%"),
                )
                entity_ids.update(row["id"] for row in entity_search)

                # Search observations by content
                obs_search = conn.execute(
                    "SELECT entity_id FROM observations WHERE content LIKE ?",
                    (f"%{query}%",),
                )
                entity_ids.update(row["entity_id"] for row in obs_search)

                # Get full entity data
                entities = []
                entity_names = set()

                if entity_ids:
                    placeholders = ",".join("?" * len(entity_ids))
                    entities_cursor = conn.execute(
                        f"SELECT id, name, entity_type FROM entities WHERE id IN ({placeholders})",
                        list(entity_ids),
                    )

                    for row in entities_cursor:
                        entity_id = row["id"]
                        entity_name = row["name"]

                        # Get observations
                        obs_cursor = conn.execute(
                            "SELECT content FROM observations WHERE entity_id = ? ORDER BY created_at",
                            (entity_id,),
                        )
                        observations = [obs_row["content"] for obs_row in obs_cursor]

                        entities.append(
                            {
                                "name": entity_name,
                                "entityType": row["entity_type"],
                                "observations": observations,
                            }
                        )
                        entity_names.add(entity_name)

                # Get relations
                if entity_names:
                    placeholders = ",".join("?" * len(entity_names))
                    relations_cursor = conn.execute(
                        f"""
                        SELECT from_entity, to_entity, relation_type
                        FROM relations
                        WHERE from_entity IN ({placeholders})
                           OR to_entity IN ({placeholders})
                    """,
                        list(entity_names) + list(entity_names),
                    )

                    relations = []
                    for row in relations_cursor:
                        relations.append(
                            {
                                "from_entity": row["from_entity"],
                                "to": row["to_entity"],
                                "relationType": row["relation_type"],
                            }
                        )
                else:
                    relations = []

                return {"entities": entities, "relations": relations}

        except Exception as e:
            print(f"Simple search failed: {e}")
            return {"entities": [], "relations": []}

    async def import_from_mcp(self, mcp_client: Any) -> dict[str, Any]:
        """Import data from an MCP client into SQLite"""
        async with self._lock:
            try:
                # Get data from MCP client
                mcp_data = await mcp_client.read_graph()

                if not mcp_data.get("entities"):
                    return {"status": "error", "message": "No data from MCP client"}

                imported_entities = 0
                imported_relations = 0
                timestamp = datetime.now(UTC).isoformat()

                with sqlite3.connect(self.db_path) as conn:
                    # Import entities
                    conn.row_factory = sqlite3.Row
                    for entity in mcp_data["entities"]:
                        try:
                            entity_name = entity["name"]
                            entity_type = entity["entityType"]
                            observations = entity.get("observations", [])

                            # Check if exists
                            cursor = conn.execute(
                                "SELECT id FROM entities WHERE name = ?",
                                (entity_name,),
                            )
                            existing = cursor.fetchone()

                            if existing:
                                entity_id = existing["id"]
                                conn.execute(
                                    "UPDATE entities SET entity_type = ?, updated_at = ? WHERE id = ?",
                                    (entity_type, timestamp, entity_id),
                                )
                            else:
                                cursor = conn.execute(
                                    """
                                    INSERT INTO entities (name, entity_type, created_at, updated_at)
                                    VALUES (?, ?, ?, ?)
                                """,
                                    (entity_name, entity_type, timestamp, timestamp),
                                )
                                entity_id = cursor.lastrowid

                            # Add observations
                            for obs_content in observations:
                                conn.execute(
                                    """
                                    INSERT INTO observations (entity_id, content, created_at)
                                    VALUES (?, ?, ?)
                                """,
                                    (entity_id, obs_content, timestamp),
                                )

                            imported_entities += 1
                        except Exception as e:
                            print(f"Failed to import entity {entity['name']}: {e}")

                    # Import relations
                    for relation in mcp_data["relations"]:
                        try:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO relations
                                (from_entity, to_entity, relation_type, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            """,
                                (
                                    relation["from_entity"],
                                    relation["to"],
                                    relation["relationType"],
                                    timestamp,
                                    timestamp,
                                ),
                            )
                            imported_relations += 1
                        except Exception as e:
                            print(f"Failed to import relation {relation}: {e}")

                    conn.commit()
                    # Force WAL checkpoint for immediate visibility
                    conn.execute("PRAGMA wal_checkpoint(FULL)")

                return {
                    "status": "success",
                    "imported_entities": imported_entities,
                    "imported_relations": imported_relations,
                    "timestamp": timestamp,
                }

            except Exception as e:
                print(f"MCP import failed: {e}")
                return {"status": "error", "message": str(e)}

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM entities) as entity_count,
                        (SELECT COUNT(*) FROM observations) as observation_count,
                        (SELECT COUNT(*) FROM relations) as relation_count,
                        (SELECT COUNT(DISTINCT entity_type) FROM entities) as entity_types,
                        (SELECT COUNT(DISTINCT relation_type) FROM relations) as relation_types
                """
                )

                stats = cursor.fetchone()
                return {
                    "entity_count": stats[0],
                    "observation_count": stats[1],
                    "relation_count": stats[2],
                    "entity_types": stats[3],
                    "relation_types": stats[4],
                    "database_path": str(self.db_path),
                }

        except Exception as e:
            print(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def create_entities(self, entities: list[dict[str, Any]]) -> None:
        """Create new entities in the database with normalized observations"""
        async with self._lock:
            timestamp = datetime.now(UTC).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                for entity in entities:
                    try:
                        entity_name = entity["name"]
                        entity_type = entity["entityType"]
                        observations = entity.get("observations", [])

                        # Check if entity exists
                        cursor = conn.execute(
                            "SELECT id FROM entities WHERE name = ?",
                            (entity_name,),
                        )
                        existing = cursor.fetchone()

                        if existing:
                            # Update existing entity
                            entity_id = existing["id"]
                            conn.execute(
                                "UPDATE entities SET entity_type = ?, updated_at = ? WHERE id = ?",
                                (entity_type, timestamp, entity_id),
                            )
                        else:
                            # Create new entity
                            cursor = conn.execute(
                                """
                                INSERT INTO entities (name, entity_type, created_at, updated_at)
                                VALUES (?, ?, ?, ?)
                            """,
                                (entity_name, entity_type, timestamp, timestamp),
                            )
                            entity_id = cursor.lastrowid

                        # Add observations
                        for obs_content in observations:
                            conn.execute(
                                """
                                INSERT INTO observations (entity_id, content, created_at)
                                VALUES (?, ?, ?)
                            """,
                                (entity_id, obs_content, timestamp),
                            )

                    except Exception as e:
                        print(f"Failed to create entity {entity['name']}: {e}")

                conn.commit()
                # Force WAL checkpoint for immediate visibility to next tool call
                conn.execute("PRAGMA wal_checkpoint(FULL)")

    async def create_relations(self, relations: list[dict[str, Any]], external_refs: list[str]) -> None:
        """Create new relations in the database

        Args:
            relations: List of relation objects to create
            external_refs: List of entity names that must exist (validates before creating)
        """
        async with self._lock:
            timestamp = datetime.now(UTC).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Validate external references (now required)
                placeholders = ",".join("?" * len(external_refs))
                cursor = conn.execute(
                    f"SELECT name FROM entities WHERE name IN ({placeholders})",
                    external_refs,
                )
                found = {row["name"] for row in cursor}
                missing = set(external_refs) - found
                if missing:
                    raise ValueError(f"Referenced entities not found: {sorted(missing)}")

                for relation in relations:
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO relations
                            (from_entity, to_entity, relation_type, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                relation["from_entity"],
                                relation["to"],
                                relation["relationType"],
                                timestamp,
                                timestamp,
                            ),
                        )
                    except Exception as e:
                        print(f"Failed to create relation {relation}: {e}")

                conn.commit()
                # Force WAL checkpoint for immediate visibility to next tool call
                conn.execute("PRAGMA wal_checkpoint(FULL)")

    async def create_subgraph(
        self,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        external_refs: list[str] | None = None,
        observations: dict[str, list[str]] | None = None,
    ) -> None:
        """Create a subgraph atomically with entities, relations, and observations

        Args:
            entities: New entities to create (with their initial observations)
            relations: Relations to create
            external_refs: Existing entity names being referenced (default: [])
            observations: Additional observations to add to any entity (new or existing)
        """
        async with self._lock:
            timestamp = datetime.now(UTC).isoformat()
            external_refs = external_refs or []
            observations = observations or {}

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Validate external references exist
                if external_refs:
                    placeholders = ",".join("?" * len(external_refs))
                    cursor = conn.execute(
                        f"SELECT name FROM entities WHERE name IN ({placeholders})",
                        external_refs,
                    )
                    found = {row["name"] for row in cursor}
                    missing = set(external_refs) - found
                    if missing:
                        raise ValueError(f"Referenced entities not found: {sorted(missing)}")

                # Step 1: Create new entities with their initial observations
                created_entity_ids: dict[str, int] = {}
                for entity in entities:
                    try:
                        entity_name = entity["name"]
                        entity_type = entity["entityType"]
                        initial_obs = entity.get("observations", [])

                        # Check if entity exists
                        cursor = conn.execute(
                            "SELECT id FROM entities WHERE name = ?",
                            (entity_name,),
                        )
                        existing = cursor.fetchone()

                        if existing:
                            # Update existing entity
                            entity_id = existing["id"]
                            conn.execute(
                                "UPDATE entities SET entity_type = ?, updated_at = ? WHERE id = ?",
                                (entity_type, timestamp, entity_id),
                            )
                        else:
                            # Create new entity
                            cursor = conn.execute(
                                """
                                INSERT INTO entities (name, entity_type, created_at, updated_at)
                                VALUES (?, ?, ?, ?)
                            """,
                                (entity_name, entity_type, timestamp, timestamp),
                            )
                            entity_id = cursor.lastrowid
                        if entity_id is None:
                            raise ValueError(f"Failed to retrieve entity ID for {entity_name}")
                        created_entity_ids[entity_name] = entity_id

                        # Add initial observations
                        for obs_content in initial_obs:
                            conn.execute(
                                """
                                INSERT INTO observations (entity_id, content, created_at)
                                VALUES (?, ?, ?)
                            """,
                                (entity_id, obs_content, timestamp),
                            )

                    except Exception as e:
                        print(f"Failed to create entity {entity['name']}: {e}")
                        raise

                # Step 2: Add additional observations to both new and existing entities
                for entity_name, obs_list in observations.items():
                    try:
                        # Get entity_id (either from created entities or lookup existing)
                        if entity_name in created_entity_ids:
                            entity_id = created_entity_ids[entity_name]
                        else:
                            cursor = conn.execute(
                                "SELECT id FROM entities WHERE name = ?",
                                (entity_name,),
                            )
                            row = cursor.fetchone()
                            if not row:
                                raise ValueError(f"Entity not found for observations: {entity_name}")
                            entity_id = row["id"]

                        # Add observations
                        for obs_content in obs_list:
                            conn.execute(
                                """
                                INSERT INTO observations (entity_id, content, created_at)
                                VALUES (?, ?, ?)
                            """,
                                (entity_id, obs_content, timestamp),
                            )

                    except Exception as e:
                        print(f"Failed to add observations to {entity_name}: {e}")
                        raise

                # Step 3: Create relations
                for relation in relations:
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO relations
                            (from_entity, to_entity, relation_type, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                relation["from_entity"],
                                relation["to"],
                                relation["relationType"],
                                timestamp,
                                timestamp,
                            ),
                        )
                    except Exception as e:
                        print(f"Failed to create relation {relation}: {e}")
                        raise

                conn.commit()
                # Force WAL checkpoint for immediate visibility to next tool call
                conn.execute("PRAGMA wal_checkpoint(FULL)")

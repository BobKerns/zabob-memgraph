"""
SQLite Database Backend for Knowledge Graph

This module provides a SQLite-based storage backend for the knowledge graph,
with import functionality from MCP data sources.
"""

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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

    def __init__(self, db_path: str = "knowledge_graph.db"):
        # Ensure we use absolute path to avoid working directory issues
        if not Path(db_path).is_absolute():
            # Use the directory of this file as the base for relative paths
            base_dir = Path(__file__).parent.parent  # Go up to project root
            self.db_path = base_dir / db_path
        else:
            self.db_path = Path(db_path)

        self._lock = asyncio.Lock()
        print(f"SQLite database path: {self.db_path.absolute()}")
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    entity_type TEXT NOT NULL,
                    observations TEXT NOT NULL,  -- JSON array
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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

                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (name);
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type);
                CREATE INDEX IF NOT EXISTS idx_relations_from ON relations (from_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_to ON relations (to_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_type ON relations (relation_type);

                -- Full-text search table for observations
                CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                    name, entity_type, observations, content='entities'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS entities_fts_insert AFTER INSERT ON entities BEGIN
                    INSERT INTO entities_fts(rowid, name, entity_type, observations)
                    VALUES (new.id, new.name, new.entity_type, new.observations);
                END;

                CREATE TRIGGER IF NOT EXISTS entities_fts_delete AFTER DELETE ON entities BEGIN
                    DELETE FROM entities_fts WHERE rowid = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS entities_fts_update AFTER UPDATE ON entities BEGIN
                    DELETE FROM entities_fts WHERE rowid = old.id;
                    INSERT INTO entities_fts(rowid, name, entity_type, observations)
                    VALUES (new.id, new.name, new.entity_type, new.observations);
                END;
            """
            )

    async def read_graph(self) -> dict[str, Any]:
        """Read the complete knowledge graph from SQLite"""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row

                    # Get all entities
                    entities_cursor = conn.execute(
                        """
                        SELECT name, entity_type, observations
                        FROM entities
                        ORDER BY name
                    """
                    )

                    entities = []
                    for row in entities_cursor:
                        entities.append(
                            {
                                "name": row["name"],
                                "entityType": row["entity_type"],
                                "observations": json.loads(row["observations"]),
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
        """Search nodes using SQLite FTS"""
        async with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row

                    # Use FTS for searching
                    search_cursor = conn.execute(
                        """
                        SELECT e.name, e.entity_type, e.observations
                        FROM entities e
                        JOIN entities_fts fts ON e.id = fts.rowid
                        WHERE entities_fts MATCH ?
                        ORDER BY rank
                    """,
                        (query,),
                    )

                    entities = []
                    entity_names = set()

                    for row in search_cursor:
                        entity_name = row["name"]
                        entities.append(
                            {
                                "name": entity_name,
                                "entityType": row["entity_type"],
                                "observations": json.loads(row["observations"]),
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

                # Simple search in name and observations
                search_cursor = conn.execute(
                    """
                    SELECT name, entity_type, observations
                    FROM entities
                    WHERE name LIKE ? OR observations LIKE ?
                    ORDER BY name
                """,
                    (f"%{query}%", f"%{query}%"),
                )

                entities = []
                entity_names = set()

                for row in search_cursor:
                    entity_name = row["name"]
                    entities.append(
                        {
                            "name": entity_name,
                            "entityType": row["entity_type"],
                            "observations": json.loads(row["observations"]),
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
                timestamp = datetime.utcnow().isoformat()

                with sqlite3.connect(self.db_path) as conn:
                    # Import entities
                    for entity in mcp_data["entities"]:
                        try:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO entities
                                (name, entity_type, observations, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            """,
                                (
                                    entity["name"],
                                    entity["entityType"],
                                    json.dumps(entity["observations"]),
                                    timestamp,
                                    timestamp,
                                ),
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
                        (SELECT COUNT(*) FROM relations) as relation_count,
                        (SELECT COUNT(DISTINCT entity_type) FROM entities) as entity_types,
                        (SELECT COUNT(DISTINCT relation_type) FROM relations) as relation_types
                """
                )

                stats = cursor.fetchone()
                return {
                    "entity_count": stats[0],
                    "relation_count": stats[1],
                    "entity_types": stats[2],
                    "relation_types": stats[3],
                    "database_path": str(self.db_path),
                }

        except Exception as e:
            print(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def create_entities(self, entities: list[dict[str, Any]]) -> None:
        """Create new entities in the database"""
        async with self._lock:
            timestamp = datetime.utcnow().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                for entity in entities:
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO entities
                            (name, entity_type, observations, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                entity["name"],
                                entity["entityType"],
                                json.dumps(entity["observations"]),
                                timestamp,
                                timestamp,
                            ),
                        )
                    except Exception as e:
                        print(f"Failed to create entity {entity['name']}: {e}")

                conn.commit()

    async def create_relations(self, relations: list[dict[str, Any]]) -> None:
        """Create new relations in the database"""
        async with self._lock:
            timestamp = datetime.utcnow().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                for relation in relations:
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO relations
                            (from_entity, to_entity, relation_type, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                relation["from"],
                                relation["to"],
                                relation["relationType"],
                                timestamp,
                                timestamp,
                            ),
                        )
                    except Exception as e:
                        print(f"Failed to create relation {relation}: {e}")

                conn.commit()


# Create the SQLite knowledge graph database instance
sqlite_knowledge_db = SQLiteKnowledgeGraphDB()

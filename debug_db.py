#!/usr/bin/env python3
"""
Debug SQLite database contents
"""

import sqlite3
from pathlib import Path

def check_database():
    """Check what's in the database"""
    db_path = Path("knowledge_graph.db")

    print(f"Database path: {db_path.absolute()}")
    print(f"Database exists: {db_path.exists()}")

    if db_path.exists():
        print(f"Database size: {db_path.stat().st_size} bytes")

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM entities")
                entity_count = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM relations")
                relation_count = cursor.fetchone()[0]

                print(f"Entities in database: {entity_count}")
                print(f"Relations in database: {relation_count}")

                if entity_count > 0:
                    print("\nFirst 5 entities:")
                    cursor = conn.execute("SELECT name, entity_type FROM entities LIMIT 5")
                    for row in cursor:
                        print(f"  - {row[0]} ({row[1]})")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
    else:
        print("Database file does not exist!")

if __name__ == "__main__":
    check_database()

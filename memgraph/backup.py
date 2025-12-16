"""Database backup management for Zabob Memgraph"""

import logging
import shutil
import time
import datetime
from pathlib import Path


def backup_database(db_path: Path,
                    min_backups: int = 5,
                    min_age: int = 7) -> None:
    """
    Create a backup of the database if it exists.

    Keep a minimum number of backups and remove old ones, based on age.

    Args:
        min_backups: Minimum number of backups to keep (default: 5)
        min_age: Minimum age of backups to keep in days (default: 7)
    """
    backup_dir = db_path.parent.parent / "backup"
    backup_dir.mkdir(exist_ok=True)

    # Ensure the database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        now = datetime.datetime.now(datetime.UTC)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"knowledge_graph_{timestamp}.db"

        try:
            shutil.copy2(db_path, backup_file)
            logging.info(f"Database backed up to {backup_file}")

            # Keep only the most recent backups
            backups = sorted(
                backup_dir.glob("knowledge_graph_*.db"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            now_time = time.time()
            candidates = backups[min_backups:]
            for backup in candidates:
                age_days = (now_time - backup.stat().st_mtime) / (24 * 3600)
                if age_days >= min_age:
                    backup.unlink()
                    logging.info(f"Removed old backup {backup}")

        except Exception as e:
            logging.warning(f"Could not create backup: {e}")
    else:
        logging.info("No existing database to backup")

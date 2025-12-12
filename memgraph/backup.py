"""Database backup management for Zabob Memgraph"""

import logging
import shutil
import time


from memgraph.config import get_config_dir, get_database_path


def backup_database(max_backups: int = 5) -> None:
    """Create a backup of the database if it exists

    Args:
        max_backups: Maximum number of backups to keep (default: 5)
    """
    config_dir = get_config_dir()
    db_file = get_database_path()
    backup_dir = config_dir / "backup"
    backup_dir.mkdir(exist_ok=True)

    # Ensure the database directory exists
    db_file.parent.mkdir(parents=True, exist_ok=True)

    if db_file.exists():
        timestamp = int(time.time())
        backup_file = backup_dir / f"knowledge_graph_{timestamp}.db"

        try:
            shutil.copy2(db_file, backup_file)
            logging.info(f"Database backed up to {backup_file}")

            # Keep only the most recent backups
            backups = sorted(
                backup_dir.glob("knowledge_graph_*.db"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            for old_backup in backups[max_backups:]:
                old_backup.unlink()
                logging.info(f"Removed old backup {old_backup}")

        except Exception as e:
            logging.warning(f"Could not create backup: {e}")
    else:
        logging.info("No existing database to backup")

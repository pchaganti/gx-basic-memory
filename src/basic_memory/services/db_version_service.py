"""Service for managing database lifecycle and schema updates."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from basic_memory import db
from basic_memory.config import ProjectConfig
from basic_memory.db import DatabaseType
from basic_memory.models import SCHEMA_VERSION


class DbVersionService:
    """Manages database lifecycle including initialization, backups, and schema updates."""

    def __init__(
        self,
        config: ProjectConfig,
        db_type: DatabaseType = DatabaseType.FILESYSTEM
    ):
        self.config = config
        self.db_path = Path(config.database_path)
        self.db_type = db_type

    async def create_backup(self) -> Optional[Path]:
        """Create backup of existing database file.

        Returns:
            Optional[Path]: Path to backup file if created, None if no DB exists
        """
        if self.db_type == db.DatabaseType.MEMORY:
            return None
        
        if not self.db_path.exists():
            return None

        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.with_suffix(f".{timestamp}.backup")

        try:
            self.db_path.rename(backup_path)
            logger.info(f"Created database backup: {backup_path}")
            
            # make a new empty file
            self.db_path.touch()
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return None

    async def initialize_db(self):
        """Initialize database for first use."""

        logger.info("Initializing database...")

        if self.db_type == db.DatabaseType.FILESYSTEM:
            await self.create_backup()
            
        # Drop existing tables if any
        await db.drop_db()

        # Create tables with current schema
        await db.get_or_create_db(db_path=self.db_path)

        logger.info(f"Database initialized with schema version {SCHEMA_VERSION}")

    async def check_db(self) -> bool:
        """Check database state and initialize/update if needed.

        Returns:
            bool: True if DB is ready for use, False if initialization failed
        """
        try:
            _, session_maker = await db.get_or_create_db(db_path=self.db_path)
            async with db.scoped_session(session_maker) as db_session:
                db_version = await db.get_schema_version(db_session)

                if db_version is None:
                    logger.info("No existing database found, initializing...")
                    await self.initialize_db()
                elif db_version != SCHEMA_VERSION:
                    logger.info(
                        f"Schema version mismatch (DB: {db_version}, Current: {SCHEMA_VERSION}), rebuilding..."
                    )
                    await self.initialize_db()
                else:
                    logger.info(f"Database schema version {db_version} matches current version")

            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    async def cleanup_backups(self, keep_count: int = 5):
        """Clean up old database backups, keeping the N most recent."""

        # Skip cleanup for in-memory DB
        if self.db_type == db.DatabaseType.MEMORY:
            return  

        backup_pattern = "*.backup"  # Use relative pattern
        backups = sorted(
            self.db_path.parent.glob(backup_pattern),  # Use parent dir for glob
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Remove old backups
        for backup in backups[keep_count:]:
            try:
                backup.unlink()
                logger.debug(f"Removed old backup: {backup}")
            except Exception as e:
                logger.error(f"Failed to remove backup {backup}: {e}")

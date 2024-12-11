"""Debugging utilities for test suite."""
from sqlalchemy import text, inspect, MetaData, Table
from sqlalchemy.ext.asyncio import AsyncEngine
from loguru import logger

async def dump_sqlite_master(conn) -> None:
    """Dump entire sqlite_master table to see what SQLite thinks exists."""
    try:
        # Check if sqlite_master exists first
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
        ))
        if result.scalar():
            result = await conn.execute(text("SELECT * FROM sqlite_master;"))
            rows = result.all()
            logger.info("SQLITE_MASTER TABLE CONTENTS:")
            for row in rows:
                logger.info(f"{row}")
        else:
            logger.info("No tables exist in sqlite_master")
    except Exception as e:
        logger.warning(f"Could not dump sqlite_master: {e}")

async def dump_table_schema(conn, table_name: str) -> None:
    """Dump detailed schema info for a specific table."""
    try:
        logger.info(f"\nDETAILED SCHEMA FOR {table_name}:")
        
        # Get CREATE statement
        result = await conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name}
        )
        create_sql = result.scalar()
        if create_sql:
            logger.info(f"CREATE statement:\n{create_sql}")
        else:
            logger.info(f"No CREATE statement found for {table_name}")

        # Get column info
        result = await conn.execute(text(f"PRAGMA table_info('{table_name}');"))
        columns = result.all()
        if columns:
            logger.info("Column definitions:")
            for col in columns:
                logger.info(f"  {col}")
        else:
            logger.info("No column definitions found")

    except Exception as e:
        logger.warning(f"Could not dump schema for {table_name}: {e}")

async def dump_sqlalchemy_metadata(engine: AsyncEngine) -> None:
    """Dump SQLAlchemy's view of the table metadata."""
    try:
        inspector = inspect(engine)
        
        logger.info("\nSQLALCHEMY METADATA:")
        # Get all tables
        tables = await inspector.get_table_names()
        if not tables:
            logger.info("No tables found in SQLAlchemy metadata")
            return
            
        for table in tables:
            logger.info(f"\nTable: {table}")
            # Get columns
            columns = await inspector.get_columns(table)
            if columns:
                logger.info("Columns:")
                for col in columns:
                    logger.info(f"  {col}")
            
            # Get indexes
            indexes = await inspector.get_indexes(table)
            if indexes:
                logger.info("Indexes:")
                for idx in indexes:
                    logger.info(f"  {idx}")
            
            # Get foreign keys
            fks = await inspector.get_foreign_keys(table)
            if fks:
                logger.info("Foreign keys:")
                for fk in fks:
                    logger.info(f"  {fk}")
    except Exception as e:
        logger.warning(f"Could not dump SQLAlchemy metadata: {e}")

async def dump_db_state(engine: AsyncEngine) -> None:
    """Dump complete database state for debugging."""
    logger.info("\n=== BEGINNING DATABASE STATE DUMP ===\n")
    
    try:
        async with engine.begin() as conn:
            # First dump sqlite_master
            await dump_sqlite_master(conn)
            
            # Try to get list of tables
            try:
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ))
                tables = [row[0] for row in result.all()]
                
                # Dump each table's schema
                for table in tables:
                    await dump_table_schema(conn, table)
            except Exception as e:
                logger.warning(f"Could not list tables: {e}")
        
        # Dump SQLAlchemy's view
        await dump_sqlalchemy_metadata(engine)
        
    except Exception as e:
        logger.warning(f"Error during state dump: {e}")
    
    logger.info("\n=== END DATABASE STATE DUMP ===\n")
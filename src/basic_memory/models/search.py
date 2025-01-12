"""Search models and tables."""

from sqlalchemy import DDL

# Define FTS5 virtual table creation
CREATE_SEARCH_INDEX = DDL("""
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    content,           -- Searchable text content
    permalink UNINDEXED, -- Link to entity/document (must be unique)
    file_path UNINDEXED, -- Filesystem path
    type UNINDEXED,    -- 'entity' or 'document'
    metadata UNINDEXED, -- JSON with timestamps, types, etc.
    tokenize='porter unicode61' -- Enable stemming + unicode
);
""")

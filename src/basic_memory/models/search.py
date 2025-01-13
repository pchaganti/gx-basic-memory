"""Search models and tables."""

from sqlalchemy import DDL

# Define FTS5 virtual table creation
CREATE_SEARCH_INDEX = DDL("""
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    title,            -- Title for exact/fuzzy matching
    content,          -- Additional searchable content
    permalink UNINDEXED, -- Link to entity/document
    file_path UNINDEXED, -- Filesystem path
    type UNINDEXED,    -- entity type
    metadata UNINDEXED, -- Additional metadata
    tokenize='porter unicode61' -- Enable stemming + unicode
);
""")

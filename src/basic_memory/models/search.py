"""Search models and tables."""

from sqlalchemy import DDL

# Define FTS5 virtual table creation
CREATE_SEARCH_INDEX = DDL("""
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    id UNINDEXED,     -- row id of the indexed item 
    title,            -- Title for exact/fuzzy matching
    content,          -- Additional searchable content
    permalink UNINDEXED, -- Link to entity
    file_path UNINDEXED, -- Filesystem path
    type UNINDEXED,    -- entity type
    metadata UNINDEXED, -- Additional metadata
    
    -- Use unicode61 for basic tokenization with prefix matching
    tokenize='unicode61 remove_diacritics 2',
    prefix='2,3'     -- Enable prefix matching for 2-3 char prefixes
);
""")
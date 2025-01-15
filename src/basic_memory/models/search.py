"""Search models and tables."""

from sqlalchemy import DDL

# Define FTS5 virtual table creation
CREATE_SEARCH_INDEX = DDL("""
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    -- Core entity fields
    id UNINDEXED,          -- Row ID
    title,                 -- Title for searching
    content,               -- Main searchable content
    permalink UNINDEXED,   -- Stable identifier
    file_path UNINDEXED,  -- Physical location
    type UNINDEXED,       -- entity/relation/observation
    
    -- Relation fields 
    from_id UNINDEXED,    -- Source entity
    to_id UNINDEXED,      -- Target entity
    relation_type UNINDEXED, -- Type of relation
    
    -- Observation fields
    entity_id UNINDEXED,  -- Parent entity
    category UNINDEXED,   -- Observation category
    
    -- Common fields
    metadata UNINDEXED,    -- JSON metadata
    created_at UNINDEXED,  -- Creation timestamp
    updated_at UNINDEXED,  -- Last update
    
    -- Configuration
    tokenize='porter unicode61',
    prefix='2,3',
    content='title content'  -- Default searchable columns
);

-- Add index for relation traversal
CREATE INDEX IF NOT EXISTS idx_search_relations 
ON search_index(from_id, to_id) WHERE type = 'relation';

-- Add index for type filtering
CREATE INDEX IF NOT EXISTS idx_search_type_perm 
ON search_index(type);
""")
-- migrate:up
-- Entities table stores core entity information
CREATE TABLE entities (
    id TEXT PRIMARY KEY,           -- timestamp-based ID (e.g., 20240101-entity-name)
    name TEXT NOT NULL,            -- human readable name
    type TEXT NOT NULL,            -- entity type (e.g., Person, Project, etc)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context TEXT,                  -- where this entity came from
    description TEXT,              -- main body content
    "references" TEXT              -- reference list content
);

-- Observations are atomic facts about entities
CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    content TEXT NOT NULL,         -- the actual observation text
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context TEXT,                  -- where this observation came from
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

-- Relations connect entities with typed, directional relationships
CREATE TABLE relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity_id TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,   -- the verb describing the relationship
    context TEXT,                  -- optional context about the relationship
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_entity_id) REFERENCES entities(id),
    FOREIGN KEY (to_entity_id) REFERENCES entities(id),
    -- Ensure we don't duplicate the exact same relationship
    UNIQUE(from_entity_id, to_entity_id, relation_type)
);

-- migrate:down
DROP TABLE IF EXISTS relations;
DROP TABLE IF EXISTS observations;
DROP TABLE IF EXISTS entities;
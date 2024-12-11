-- migrate:up
-- Make description column explicitly nullable by recreating table
CREATE TABLE entity_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT NULL,
    "references" TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Copy existing data
INSERT INTO entity_new (id, name,  entity_type, description, "references", created_at)
SELECT id, name,   entity_type, description, "references", created_at FROM entity;

-- Drop old table and rename new one
DROP TABLE entity;
ALTER TABLE entity_new RENAME TO entity;

-- migrate:down
-- Restore NOT NULL constraint by recreating table
CREATE TABLE entity_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    "references" TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
);

-- Copy data (will fail if any nulls exist)
INSERT INTO entity_new (id, name,   entity_type, description, "references", created_at)
SELECT id, name,   entity_type, description, "references", created_at FROM entity;

-- Drop old table and rename new one
DROP TABLE entity;
ALTER TABLE entity_new RENAME TO entity;
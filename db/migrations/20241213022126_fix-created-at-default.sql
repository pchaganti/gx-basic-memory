-- migrate:up

-- Create new observation table with correct default
CREATE TABLE observation_new (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
    entity_id VARCHAR NOT NULL, 
    content VARCHAR NOT NULL, 
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    context VARCHAR,
    FOREIGN KEY(entity_id) REFERENCES entity (id) ON DELETE CASCADE
);

-- Copy data from old observation table
INSERT INTO observation_new 
SELECT id, entity_id, content, COALESCE(created_at, CURRENT_TIMESTAMP), context 
FROM observation;

-- Drop old observation table and rename new one
DROP TABLE observation;
ALTER TABLE observation_new RENAME TO observation;

-- Recreate observation index
CREATE INDEX ix_observation_entity_id ON observation (entity_id);

-- Create new relation table with correct default
CREATE TABLE relation_new (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
    from_id VARCHAR NOT NULL, 
    to_id VARCHAR NOT NULL, 
    relation_type VARCHAR NOT NULL, 
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    context VARCHAR,
    FOREIGN KEY(from_id) REFERENCES entity (id) ON DELETE CASCADE,
    FOREIGN KEY(to_id) REFERENCES entity (id) ON DELETE CASCADE
);

-- Copy data from old relation table
INSERT INTO relation_new 
SELECT id, from_id, to_id, relation_type, COALESCE(created_at, CURRENT_TIMESTAMP), context 
FROM relation;

-- Drop old relation table and rename new one
DROP TABLE relation;
ALTER TABLE relation_new RENAME TO relation;

-- Recreate relation indexes
CREATE INDEX ix_relation_from_id ON relation (from_id);
CREATE INDEX ix_relation_to_id ON relation (to_id);

-- migrate:down

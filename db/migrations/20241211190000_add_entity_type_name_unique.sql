-- migrate:up
-- Add unique index on entity type and name combination
CREATE UNIQUE INDEX idx_entity_type_name ON entity(entity_type, name);

-- migrate:down

-- Restore original schema
DROP INDEX IF EXISTS idx_entity_type_name;
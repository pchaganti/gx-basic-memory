CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE IF NOT EXISTS "entity" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_entity_type_name ON entity(entity_type, name);
CREATE TABLE IF NOT EXISTS "observation" (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    entity_id VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context VARCHAR,
    FOREIGN KEY(entity_id) REFERENCES entity (id) ON DELETE CASCADE
);
CREATE INDEX ix_observation_entity_id ON observation (entity_id);
CREATE TABLE IF NOT EXISTS "relation" (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    from_id VARCHAR NOT NULL,
    to_id VARCHAR NOT NULL,
    relation_type VARCHAR NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    context VARCHAR,
    FOREIGN KEY(from_id) REFERENCES entity (id) ON DELETE CASCADE,
    FOREIGN KEY(to_id) REFERENCES entity (id) ON DELETE CASCADE
);
CREATE INDEX ix_relation_from_id ON relation (from_id);
CREATE INDEX ix_relation_to_id ON relation (to_id);
-- Dbmate schema migrations
INSERT INTO "schema_migrations" (version) VALUES
  ('20240101000000'),
  ('20241210213454'),
  ('20241211034719'),
  ('20241211052101'),
  ('20241211190000'),
  ('20241213022126');

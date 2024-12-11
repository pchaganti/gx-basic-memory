CREATE TABLE observation (
	id INTEGER NOT NULL,
	entity_id VARCHAR NOT NULL,
	content VARCHAR NOT NULL,
	created_at DATETIME NOT NULL,
	context VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(entity_id) REFERENCES entity (id) ON DELETE CASCADE
);
CREATE INDEX ix_observation_entity_id ON observation (entity_id);
CREATE TABLE relation (
	id INTEGER NOT NULL,
	from_id VARCHAR NOT NULL,
	to_id VARCHAR NOT NULL,
	relation_type VARCHAR NOT NULL,
	created_at DATETIME NOT NULL,
	context VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(from_id) REFERENCES entity (id) ON DELETE CASCADE,
	FOREIGN KEY(to_id) REFERENCES entity (id) ON DELETE CASCADE
);
CREATE INDEX ix_relation_to_id ON relation (to_id);
CREATE INDEX ix_relation_from_id ON relation (from_id);
CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE IF NOT EXISTS "entity" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Dbmate schema migrations
INSERT INTO "schema_migrations" (version) VALUES
  ('20240101000000'),
  ('20241210213454'),
  ('20241211034719'),
  ('20241211052101');

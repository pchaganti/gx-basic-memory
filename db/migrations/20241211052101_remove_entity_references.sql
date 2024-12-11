-- migrate:up
ALTER TABLE entity DROP COLUMN "references";

-- migrate:down
ALTER TABLE entity ADD COLUMN "references" TEXT DEFAULT NULL;
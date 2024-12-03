-- migrate:up

-- Rename tables to singular form
ALTER TABLE entities RENAME TO entity;
ALTER TABLE observations RENAME TO observation;
ALTER TABLE relations RENAME TO relation;

-- migrate:down

-- Remove new columns from entity table
ALTER TABLE entity DROP COLUMN "references";
ALTER TABLE entity DROP COLUMN description;

-- Rename tables back to plural form
ALTER TABLE relation RENAME TO relations;
ALTER TABLE observation RENAME TO observations;
ALTER TABLE entity RENAME TO entities;

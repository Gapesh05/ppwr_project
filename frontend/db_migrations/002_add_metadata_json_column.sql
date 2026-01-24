-- Migration: add metadata_json column to supplier_declarations if needed
BEGIN;

ALTER TABLE IF EXISTS supplier_declarations
    ADD COLUMN IF NOT EXISTS metadata_json jsonb;

CREATE INDEX IF NOT EXISTS supplier_declarations_metadata_json_gin ON supplier_declarations USING gin (metadata_json);

COMMIT;

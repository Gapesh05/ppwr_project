-- Migration: synchronize supplier_declarations with ORM model and set defaults
BEGIN;

-- Add missing columns used by ORM if they don't exist
ALTER TABLE IF EXISTS supplier_declarations
    ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255),
    ADD COLUMN IF NOT EXISTS storage_filename VARCHAR(1000),
    ADD COLUMN IF NOT EXISTS file_path VARCHAR(1000),
    ADD COLUMN IF NOT EXISTS document_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS upload_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS upload_timestamp INTEGER,
    ADD COLUMN IF NOT EXISTS upload_timestamp_ms BIGINT,
    ADD COLUMN IF NOT EXISTS file_size BIGINT,
    ADD COLUMN IF NOT EXISTS file_data BYTEA,
    ADD COLUMN IF NOT EXISTS metadata_json JSONB;

-- Ensure GIN index on metadata_json exists (safe if already created)
CREATE INDEX IF NOT EXISTS supplier_declarations_metadata_json_gin ON supplier_declarations USING gin (metadata_json);

-- If an is_encrypted column exists, ensure it has a safe default and is not null
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'is_encrypted'
    ) THEN
        -- set default to false so inserts can omit this field
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN is_encrypted SET DEFAULT false';
        -- backfill nulls
        EXECUTE 'UPDATE supplier_declarations SET is_encrypted = false WHERE is_encrypted IS NULL';
        -- keep it not null for data hygiene
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN is_encrypted SET NOT NULL';
    END IF;
END $$;

COMMIT;

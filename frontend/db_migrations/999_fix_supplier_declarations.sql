-- Safe fix-up migration to reconcile supplier_declarations schema
BEGIN;

-- Ensure table exists minimally
CREATE TABLE IF NOT EXISTS supplier_declarations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL
);

-- Add expected columns if missing
ALTER TABLE supplier_declarations
    ADD COLUMN IF NOT EXISTS sku VARCHAR(100),
    ADD COLUMN IF NOT EXISTS material VARCHAR(100),
    ADD COLUMN IF NOT EXISTS filename VARCHAR(255),
    ADD COLUMN IF NOT EXISTS stored_path VARCHAR(1000),
    ADD COLUMN IF NOT EXISTS content_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS metadata_json JSONB,
    ADD COLUMN IF NOT EXISTS file_size BIGINT,
    ADD COLUMN IF NOT EXISTS file_data BYTEA;

-- Drop NOT NULL on stored_path (DB-only storage now allowed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations'
          AND column_name = 'stored_path'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE supplier_declarations ALTER COLUMN stored_path DROP NOT NULL;
    END IF;
END $$;

-- Create indexes if missing
CREATE INDEX IF NOT EXISTS supplier_declarations_sku_idx ON supplier_declarations (sku);
CREATE INDEX IF NOT EXISTS supplier_declarations_material_idx ON supplier_declarations (material);
CREATE INDEX IF NOT EXISTS supplier_declarations_metadata_json_gin ON supplier_declarations USING gin (metadata_json);

-- Relax NOT NULL constraints on legacy columns we no longer populate
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'document_type' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE supplier_declarations ALTER COLUMN document_type DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'original_filename' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE supplier_declarations ALTER COLUMN original_filename DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'storage_filename' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE supplier_declarations ALTER COLUMN storage_filename DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'file_path' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE supplier_declarations ALTER COLUMN file_path DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'upload_date' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE supplier_declarations ALTER COLUMN upload_date DROP NOT NULL;
    END IF;
END $$;

COMMIT;

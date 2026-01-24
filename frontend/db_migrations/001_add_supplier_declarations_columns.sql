-- Migration: add metadata, file_size, file_data to supplier_declarations
BEGIN;

ALTER TABLE IF EXISTS supplier_declarations
    ADD COLUMN IF NOT EXISTS metadata jsonb,
    ADD COLUMN IF NOT EXISTS file_size bigint,
    ADD COLUMN IF NOT EXISTS file_data bytea;

-- Indexes for queries on metadata
CREATE INDEX IF NOT EXISTS supplier_declarations_metadata_gin ON supplier_declarations USING gin (metadata);
CREATE INDEX IF NOT EXISTS supplier_declarations_sku_idx ON supplier_declarations (sku);
CREATE INDEX IF NOT EXISTS supplier_declarations_material_idx ON supplier_declarations (material);

COMMIT;

-- Migration: set defaults for additional enforced columns on supplier_declarations
BEGIN;

DO $$
BEGIN
    -- is_archived: default false, not null
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'is_archived'
    ) THEN
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN is_archived SET DEFAULT false';
        EXECUTE 'UPDATE supplier_declarations SET is_archived = false WHERE is_archived IS NULL';
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN is_archived SET NOT NULL';
    END IF;
END $$;

COMMIT;

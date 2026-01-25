-- Migration: ensure defaults for extra enforced columns so inserts work
BEGIN;

DO $$
BEGIN
    -- access_count: default 0, not null
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'access_count'
    ) THEN
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN access_count SET DEFAULT 0';
        EXECUTE 'UPDATE supplier_declarations SET access_count = 0 WHERE access_count IS NULL';
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN access_count SET NOT NULL';
    END IF;

    -- is_encrypted: default false, not null
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_declarations' AND column_name = 'is_encrypted'
    ) THEN
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN is_encrypted SET DEFAULT false';
        EXECUTE 'UPDATE supplier_declarations SET is_encrypted = false WHERE is_encrypted IS NULL';
        EXECUTE 'ALTER TABLE supplier_declarations ALTER COLUMN is_encrypted SET NOT NULL';
    END IF;
END $$;

COMMIT;

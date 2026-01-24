-- Migration: make stored_path nullable to support DB-only storage
BEGIN;

ALTER TABLE IF EXISTS supplier_declarations
    ALTER COLUMN stored_path DROP NOT NULL;

COMMIT;

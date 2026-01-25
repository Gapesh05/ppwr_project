-- Adds ppwr_flag to PFAS BOM table for PPWR-only ingestion gating
ALTER TABLE pfas_bom ADD COLUMN IF NOT EXISTS ppwr_flag BOOLEAN DEFAULT FALSE;
-- Migration: Add uploaded_at column to ppwr_bom table
-- Purpose: Track when BOM materials were uploaded for display in PPWR tab

ALTER TABLE ppwr_bom 
ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create index for efficient timestamp queries
CREATE INDEX IF NOT EXISTS idx_ppwr_bom_uploaded_at ON ppwr_bom(uploaded_at);

-- Backfill existing rows with current timestamp
UPDATE ppwr_bom 
SET uploaded_at = CURRENT_TIMESTAMP 
WHERE uploaded_at IS NULL;

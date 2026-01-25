-- Migration 016: Add performance indexes for frequently queried columns
-- Purpose: Speed up queries filtering by supplier_name and status

-- Add index on ppwr_bom.supplier_name for supplier filtering
CREATE INDEX IF NOT EXISTS idx_ppwr_bom_supplier 
ON ppwr_bom(supplier_name);

-- Add index on ppwr_result.status for status filtering  
CREATE INDEX IF NOT EXISTS idx_ppwr_result_status 
ON ppwr_result(status);

-- Verify indexes were created
SELECT 
    schemaname,
    tablename, 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('ppwr_bom', 'ppwr_result')
AND indexname IN ('idx_ppwr_bom_supplier', 'idx_ppwr_result_status')
ORDER BY tablename, indexname;

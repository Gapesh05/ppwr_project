-- Migration 017: Drop deprecated ppwr_assessments table
-- Date: 2026-01-25
-- Reason: RAG pipeline consolidated to use ppwr_result table instead
-- Impact: Removes duplicate storage, unifies manual and RAG-extracted data

-- Drop ppwr_assessments table (replaced by ppwr_result)
DROP TABLE IF EXISTS ppwr_assessments CASCADE;

-- This table stored RAG extraction results with rich metadata:
--   - material_id (PK)
--   - supplier_name
--   - declaration_date
--   - ppwr_compliant (boolean)
--   - packaging_recyclability
--   - recycled_content_percent
--   - restricted_substances_json (array)
--   - notes
--   - source_path
--   - regulatory_mentions_json (array)
--   - created_at, updated_at

-- Now consolidated into ppwr_result with simplified schema:
--   - material_id (PK)
--   - supplier_name
--   - cas_id
--   - chemical (joined restricted substances string)
--   - concentration (float)
--   - status ('Compliant'/'Non-Compliant')

-- Benefits of consolidation:
--   ✅ Single source of truth for PPWR data
--   ✅ Automatic integration with evaluation UI
--   ✅ No frontend changes required
--   ✅ Backward compatible with manual data entry

-- Trade-offs:
--   ⚠️ Rich metadata not stored (packaging_recyclability, declaration_date)
--   ⚠️ Regulatory mentions logged but not persisted
--   ⚠️ Simplified schema loses some analytical depth

-- Rollback: If needed, recreate table using git history:
-- git show HEAD~1:backend/models.py | grep -A 15 "class PPWRAssessment"

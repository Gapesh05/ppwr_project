# PFAS/PPWR Schema Alignment - Implementation Summary

## ✅ Changes Implemented

### 1. Database Migration
**File:** `frontend/db_migrations/015_add_uploaded_at_to_ppwr_bom.sql`
- Added `uploaded_at` TIMESTAMP column to `ppwr_bom` table
- Created index for efficient timestamp queries
- Backfilled existing rows with current timestamp

### 2. Frontend Models (`frontend/models.py`)
**Fixed Schema Mismatches:**
- ✅ `SupplierDeclaration` → `SupplierDeclarationV1`
  - Changed primary key from `material_id` (VARCHAR) to `id` (INTEGER autoincrement)
  - Updated `__tablename__` from `'supplier_declarations'` to `'supplier_declaration_v1'`
  - Simplified to match actual database structure
  
- ✅ Added `PPWRResult` model (was missing)
  - Maps to existing `ppwr_result` table in database
  - Columns: material_id, cas_id, supplier_name, status, chemical, concentration
  
- ✅ Updated `PPWRBOM` model
  - Added component, component_description, subcomponent, subcomponent_description columns
  - Added uploaded_at column (after migration)
  
- ✅ Fixed `PPWRMaterialDeclarationLink`
  - Changed `__tablename__` from plural `'ppwr_material_declaration_links'` to singular `'ppwr_material_declaration_link'`
  - Updated to reference `decl_material_v1` (declaration ID) instead of deprecated decl_id

**Removed Duplicate/Unused Models:**
- ❌ Removed: Old `SupplierDeclaration` model (wrong table name, wrong primary key)

### 3. Backend Models (`backend/models.py`)
**Fixed Schema Mismatches:**
- ✅ Removed `PPWRAssessment` model (table doesn't exist in database)
- ✅ Added `PPWRResult` model matching frontend
- ✅ Added `SupplierDeclarationV1` model with correct structure
- ✅ Updated `PPWRBOM` to include component/subcomponent columns
- ✅ Fixed `PPWRMaterialDeclarationLink` table name (plural → singular)
- ✅ Updated `init_backend_db()` to ensure uploaded_at column exists

### 4. Frontend Routes (`frontend/app.py`)
**Updated Imports:**
- Changed from `SupplierDeclaration` to `SupplierDeclarationV1`
- Added `PPWRResult` to imports

**Updated Evaluation Page Route (`/ppwr/evaluation`):**
- Now queries actual database tables: `ppwr_result` + `ppwr_bom`
- Added SKU filtering via query parameter `?sku=<value>`
- Returns correct columns in order: Component, Subcomponent, Material, Supplier, CAS_ID, Chemical, Concentration, Status
- Calculates accurate statistics (total materials, materials with results, conformance/non-conformance)

**Updated Helper Functions:**
- `_build_distinct_ppwr_declarations()` now uses `SupplierDeclarationV1.query`

### 5. Backend Routes (`backend/main.py`)
**Updated Imports:**
- Changed from `PPWRAssessment` to `PPWRResult`
- Added `SupplierDeclarationV1` to imports

**Updated API Endpoints:**
- `/ppwr/assessments` now queries `ppwr_result` table
- `/ppwr/evaluation/summary` now joins `ppwr_result` + `ppwr_bom` for complete data

## 📊 Database Schema Alignment

### Before (❌ Wrong):
```
Code Models          Database Tables
-------------------------------------
SupplierDeclaration  ❌ supplier_declarations (doesn't exist)
  PK: material_id    
                     
PPWRAssessment       ❌ ppwr_assessments (doesn't exist)

ppwr_material_       ❌ ppwr_material_declaration_links (plural)
declaration_links
```

### After (✅ Correct):
```
Code Models                  Database Tables
------------------------------------------------
SupplierDeclarationV1   →   ✅ supplier_declaration_v1
  PK: id (INTEGER)
                     
PPWRResult              →   ✅ ppwr_result

PPWRMaterialDeclaration →   ✅ ppwr_material_declaration_link (singular)
Link

PPWRBOM                 →   ✅ ppwr_bom
  (with uploaded_at)          (with uploaded_at after migration)
```

## 🔗 Table Relationships

```
┌─────────────────────┐
│   ppwr_bom          │
│  (BOM materials)    │
│                     │
│  PK: material_id    │
│  - sku              │
│  - component        │
│  - subcomponent     │
│  - uploaded_at ✨   │
└──────┬──────────────┘
       │
       │ LEFT JOIN
       ↓
┌─────────────────────┐
│   ppwr_result       │
│ (Chemical data)     │
│                     │
│  PK: material_id    │
│  - cas_id           │
│  - chemical         │
│  - concentration    │
│  - status           │
└─────────────────────┘

┌─────────────────────────┐
│ supplier_declaration_v1 │
│   (PDF storage)         │
│                         │
│  PK: id ✨              │
│  - material_id          │
│  - file_data (BYTEA)    │
│  - upload_date          │
└────────┬────────────────┘
         │
         │ referenced by
         ↓
┌──────────────────────────┐
│ ppwr_material_          │
│ declaration_link        │
│ (Mapping table)         │
│                         │
│  - material_id          │
│  - decl_material_v1 ✨  │
└─────────────────────────┘
```

## 🚀 Running the Migration

```bash
cd /home/gapesh/Downloads/PFAS_V0.2/frontend
python run_migrations.py
```

**Verify:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'ppwr_bom' AND column_name = 'uploaded_at';
```

## 🎯 Workflow Routes Connected

### Dashboard (`/`)
- **Data Source:** `route` table + `ppwr_bom` table
- **Display:** Products grouped by SKU with upload timestamps
- **Columns:** SKU, Product Name, Route (PFAS/PPWR), Uploaded At ✨

### PPWR Assessment Tab (`/assessment/<sku>?tab=ppwr`)
- **Data Source:** `ppwr_bom` + `supplier_declaration_v1`
- **Display:** Materials with supplier declarations
- **Actions:** Upload, Map, View Evaluation
- **Shows:** Material ID, File, Upload Time ✨, Supplier Campaign

### Evaluation Page (`/ppwr/evaluation?sku=<value>`)
- **Data Source:** `ppwr_result` ⟷ `ppwr_bom` (LEFT JOIN)
- **Display:** Component, Subcomponent, Material, Supplier, CAS_ID, Chemical, Concentration, Status
- **Stats:** Total files, Files downloaded, Conformance, Non-conformance
- **SKU Filtering:** ✅ Supported via query parameter

## 📝 Code Changes Summary

| File | Lines Changed | Type |
|------|---------------|------|
| `frontend/db_migrations/015_add_uploaded_at_to_ppwr_bom.sql` | +10 | New |
| `frontend/models.py` | ~80 | Modified |
| `backend/models.py` | ~60 | Modified |
| `frontend/app.py` | ~120 | Modified |
| `backend/main.py` | ~40 | Modified |
| **Total** | **~310 lines** | **5 files** |

## ✨ Key Improvements

1. **Schema Alignment:** All models now match actual database structure
2. **Correct Primary Keys:** `supplier_declaration_v1` uses INTEGER id (not material_id)
3. **Component/Subcomponent Data:** Now available in PPWRBOM for evaluation display
4. **Upload Timestamps:** Dashboard and PPWR tab show when materials were uploaded
5. **Evaluation Page Fixed:** Queries correct tables with proper JOIN
6. **SKU Filtering:** Evaluation page can filter by specific SKU
7. **Removed Dead Code:** Eliminated references to non-existent tables

## ⚠️ Breaking Changes

- **SupplierDeclaration** → **SupplierDeclarationV1** (all references updated)
- **PPWRAssessment** → **PPWRResult** (all references updated)
- **Primary key change:** Declaration storage now uses auto-increment `id` instead of `material_id`

## 🧪 Testing Checklist

- [ ] Run migration: `python frontend/run_migrations.py`
- [ ] Restart services: `docker compose restart`
- [ ] Access dashboard: Verify products show upload times
- [ ] Access PPWR tab: Verify declarations load correctly
- [ ] Upload new declaration: Verify storage in supplier_declaration_v1
- [ ] View evaluation: Verify component/subcomponent/chemical data displays
- [ ] Test SKU filter: Verify `/ppwr/evaluation?sku=TEST123` works
- [ ] Check logs: Verify no RelationError or NoSuchColumnError

## 📚 Reference

- Database screenshots: Provided by user showing actual schema
- Migration strategy: ADD COLUMN IF NOT EXISTS (idempotent)
- Model alignment: Code now reflects database reality, not assumptions

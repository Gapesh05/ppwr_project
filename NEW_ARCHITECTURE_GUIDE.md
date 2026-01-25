# PFAS/PPWR New Architecture Guide

## Overview

This document describes the **new PPWRBOM-driven architecture** that replaces the old PFASBOM-centric model. The new design eliminates file storage and uses `ppwr_bom` as the single source of truth for material data, with a slim `route` table for routing decisions.

---

## ✅ What Changed

### Database Schema

**OLD (PFASBOM-based):**
```
pfas_bom:
  - sku (PK)
  - product
  - uploaded_at
  - files_data (BYTEA - stored uploaded file)
  - route
```

**NEW (Route + PPWRBOM-based):**
```
route:
  - sku (PK)
  - route (pfas | ppwr)

ppwr_bom:
  - material_id (PK)
  - sku
  - material_name
  - supplier_name
  - ppwr_flag
  - uploaded_at
```

### Key Changes

1. **No More File Storage**: BOM files are no longer stored. Downloads are reconstructed from `ppwr_bom` rows.
2. **Slim Routing Table**: `route` table contains only `(sku, route)` — no product name or timestamps.
3. **Material-Centric BOM**: `ppwr_bom` stores one row per material, grouped by SKU.
4. **Derived Product Names**: Product names are derived from SKU (e.g., "Product SKU123").
5. **Deprecated Routes**: All legacy filter/export routes that queried `component`/`subcomponent` columns are deprecated (return HTTP 410).

---

## 🚀 How It Works Now

### 1. **Dashboard (Index Page)**

**Route**: `GET /`

**Data Source**: Queries `ppwr_bom` grouped by SKU, joins with `route` table.

**Logic**:
```python
# Get distinct SKUs with latest upload timestamp
ppwr_data = db.session.query(
    PPWRBOM.sku,
    func.max(PPWRBOM.uploaded_at).label('uploaded_at')
).filter(PPWRBOM.sku.isnot(None)).group_by(PPWRBOM.sku).all()

# Get routes for these SKUs
routes = db.session.query(Route).filter(Route.sku.in_(skus)).all()

# Build product list
products = []
for row in ppwr_data:
    products.append({
        'sku': row.sku,
        'product_name': f"Product {row.sku}",  # Derived name
        'route': sku_to_route.get(row.sku, 'pfas'),
        'uploaded_at': row.uploaded_at
    })
```

**UI Display**:
- Product name: "Product {SKU}"
- Download button: Reconstructs CSV from `ppwr_bom`
- Start button: Routes to PFAS or PPWR assessment based on `route` table

---

### 2. **BOM Upload**

**Route**: `POST /upload`

**Data Storage**: Populates **both** `route` and `ppwr_bom` tables.

**Logic**:
```python
# 1. Parse uploaded CSV/Excel
df = pd.read_csv(file)

# 2. Extract SKU and route
sku_val = df.iloc[0][sku_col]
route_val = 'ppwr' if 'ppwr' in request.form else 'pfas'

# 3. Upsert route table
route_rec = Route(sku=sku_val, route=route_val)
db.session.add(route_rec)

# 4. Parse materials and populate ppwr_bom
for _, row in df.iterrows():
    material_id = row['material']
    ppwr_bom_row = PPWRBOM(
        material_id=material_id,
        sku=sku_val,
        material_name=row['material_name'],
        supplier_name=row['supplier'],
        uploaded_at=datetime.utcnow()
    )
    db.session.add(ppwr_bom_row)

db.session.commit()
```

**What's Stored**:
- `route` table: One row per SKU with routing decision
- `ppwr_bom` table: One row per material with SKU reference

**What's NOT Stored**:
- ❌ Uploaded file bytes (no more `files_data` column)
- ❌ Product name (derived from SKU instead)
- ❌ Component/subcomponent (not needed for current workflows)

---

### 3. **BOM Download**

**Route**: `GET /bom/download/<sku>`

**Data Source**: Reconstructs CSV from `ppwr_bom` rows filtered by SKU.

**Logic**:
```python
# Query all materials for this SKU
materials = db.session.query(PPWRBOM).filter_by(sku=sku).all()

# Build CSV
csv_lines = ["SKU,Material ID,Material Name,Supplier,Uploaded At"]
for mat in materials:
    csv_lines.append(f"{sku},{mat.material_id},{mat.material_name},{mat.supplier_name},{mat.uploaded_at}")

# Stream as CSV
return send_file(BytesIO(csv_content.encode('utf-8')), download_name=f"BOM_{sku}.csv")
```

**Downloaded File Format**:
```csv
SKU,Material ID,Material Name,Supplier,Uploaded At
SKU123,A8362,Tyvek,SupplierA,2026-01-24 10:30:00
SKU123,B7346,PE Film,SupplierB,2026-01-24 10:30:00
```

---

### 4. **Assessment Pages**

**Routes**: 
- `GET /assessment/<sku>` (PFAS)
- `GET /ppwr-assessment/<sku>` (PPWR)

**Data Source**: Queries `ppwr_bom` + `result` (chemical data) + `pfas_regulations`.

**Logic**:
```python
# Get materials for SKU
materials = db.session.query(PPWRBOM).filter_by(sku=sku).all()

# Join with chemical data and regulations
results = db.session.query(
    PPWRBOM.material_id,
    PFASMaterialChemicals.cas_number,
    PFASMaterialChemicals.chemical_name,
    PFASMaterialChemicals.concentration_ppm,
    PFASRegulations.eu_reach_registered_ppm,
    # ... other regulatory thresholds
).join(...).filter(PPWRBOM.sku == sku).all()

# Compare concentrations against thresholds
# Render assessment table
```

**Assessment already works** because it queries `ppwr_bom` (the fallback logic was already in place).

---

### 5. **Start Button Routing**

**Route**: `GET /start/<sku>`

**Data Source**: Queries `route` table.

**Logic**:
```python
rec = db.session.query(Route).filter_by(sku=sku).first()
route_val = rec.route if rec else 'pfas'

if route_val == 'ppwr':
    return redirect(url_for('ppwr_assessment_page', sku=sku))
else:
    return redirect(url_for('assessment_page', sku=sku))
```

---

## ❌ Deprecated Routes

The following routes are **deprecated** (return HTTP 410 Gone) because they queried `PFASBOM.component/subcomponent` columns that no longer exist:

### Filter Routes
- `GET /api/skus` - Listed SKUs with product names from PFASBOM
- `GET /api/components` - Listed component hierarchy
- `GET /api/subcomponents` - Listed subcomponent hierarchy
- `GET /api/materials` - Listed materials by component/subcomponent
- `GET /api/filter-results` - Filtered materials by component/subcomponent

### Export Routes
- `POST /api/export-filter-results` - Exported filtered data with component columns

### Debug Routes
- `GET /debug-bom/<sku>` - Displayed BOM rows with component/subcomponent
- `POST /api/bom/upload` - Legacy detailed BOM API (use `/upload` instead)

**Why Deprecated?**
The new architecture uses a **flat material list** (`ppwr_bom`) without component/subcomponent hierarchy. Users access assessment pages directly via dashboard instead of using filters.

---

## 📦 Migration Steps

### Step 1: Run Migration Script

```bash
python scripts/migrate_to_route_table.py
```

This script:
1. Creates `route` table with only `(sku, route)` columns
2. Migrates data from `pfas_bom` to `route`
3. Adds `uploaded_at` column to `ppwr_bom` if missing
4. Drops `pfas_bom` table (CASCADE)

**Before Migration**:
```sql
SELECT * FROM pfas_bom LIMIT 5;
-- sku | product | uploaded_at | files_data | route
```

**After Migration**:
```sql
SELECT * FROM route LIMIT 5;
-- sku | route

SELECT * FROM ppwr_bom LIMIT 5;
-- material_id | sku | material_name | supplier_name | uploaded_at
```

### Step 2: Verify Migration

Check that:
- ✅ `route` table exists with SKUs
- ✅ `ppwr_bom` has `uploaded_at` column
- ✅ `pfas_bom` table is dropped
- ✅ Dashboard loads products from `ppwr_bom`
- ✅ Download button reconstructs CSV
- ✅ Upload creates `route` + `ppwr_bom` rows

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│                   USER UPLOADS BOM                  │
│           (CSV/Excel with SKU + Materials)          │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Parse BOM File       │
         │  Extract SKU, Route,  │
         │  Material List        │
         └───────────┬───────────┘
                     │
         ┌───────────▼────────────┐
         │  Upsert Route Table    │
         │  (sku, route)          │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │  Populate ppwr_bom     │
         │  (one row per material)│
         └───────────┬────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              DASHBOARD DISPLAY                       │
│                                                      │
│  ┌────────────┬──────────┬──────────┬────────────┐ │
│  │ Product    │ Download │ Uploaded │ Start      │ │
│  ├────────────┼──────────┼──────────┼────────────┤ │
│  │ Product    │  📥 CSV  │ 2026-... │ ▶️ Assess  │ │
│  │ SKU123     │          │          │            │ │
│  └────────────┴──────────┴──────────┴────────────┘ │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
               │                  │
    ┌──────────▼─────────┐   ┌───▼─────────────┐
    │  Download Button   │   │  Start Button   │
    │  Click             │   │  Click          │
    └──────────┬─────────┘   └───┬─────────────┘
               │                  │
    ┌──────────▼─────────┐   ┌───▼─────────────┐
    │ Query ppwr_bom     │   │ Query route     │
    │ by SKU             │   │ table           │
    └──────────┬─────────┘   └───┬─────────────┘
               │                  │
    ┌──────────▼─────────┐   ┌───▼─────────────┐
    │ Reconstruct CSV    │   │ Redirect to     │
    │ from materials     │   │ Assessment Page │
    └──────────┬─────────┘   └───┬─────────────┘
               │                  │
               ▼                  ▼
         📥 Download         🔬 Assessment
         BOM_{SKU}.csv       (PFAS or PPWR)
```

---

## ✅ Benefits of New Architecture

1. **Simplified Schema**: Only two tables for BOM management (`route` + `ppwr_bom`).
2. **No File Storage**: Eliminates BYTEA column and storage overhead.
3. **Flexible Downloads**: Can reconstruct BOM in any format (CSV, Excel, JSON) on-demand.
4. **Material-Centric**: Each material is tracked independently, making chemical data joins easier.
5. **Cleaner Routing**: Explicit `route` table makes PFAS vs PPWR distinction clear.
6. **Scalable**: No large binary columns to slow down queries.

---

## 🔧 Troubleshooting

### Problem: Dashboard shows no products
**Cause**: Migration not run or ppwr_bom is empty.
**Fix**: 
```bash
python scripts/migrate_to_route_table.py
# Then upload a BOM via UI
```

### Problem: Download button returns empty CSV
**Cause**: No ppwr_bom rows for that SKU.
**Fix**: Re-upload BOM using new upload route.

### Problem: Assessment page shows "No Data"
**Cause**: Chemical data not extracted yet.
**Fix**: Click "Run Assessment" button to trigger LLM extraction.

### Problem: Legacy filter page broken
**Expected**: Filter routes are deprecated. Use assessment pages directly.

---

## 📚 Next Steps

1. ✅ Run migration script: `python scripts/migrate_to_route_table.py`
2. ✅ Test dashboard loads products from ppwr_bom
3. ✅ Upload a new BOM and verify route + ppwr_bom population
4. ✅ Test download reconstructs CSV correctly
5. ✅ Verify assessment pages work with ppwr_bom
6. ✅ Confirm legacy filter routes return 410 errors

---

## 📝 Summary

The new architecture simplifies PFAS/PPWR workflows by:
- Using **`route`** table for routing decisions (sku → pfas/ppwr)
- Using **`ppwr_bom`** as single source of truth for materials
- **Reconstructing** downloads on-demand (no file storage)
- **Deprecating** legacy component/subcomponent filter routes

All core workflows (upload, download, assessment, routing) now work through the simplified `route + ppwr_bom` model.

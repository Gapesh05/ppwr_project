# ⚡ Next Steps - PFAS/PPWR Implementation

## 🎯 Implementation Complete!

All code changes have been successfully implemented. The database schema is now aligned with the actual PostgreSQL database.

---

## ✅ What Was Completed

### 1. Database Migration Created
- **File:** `frontend/db_migrations/015_add_uploaded_at_to_ppwr_bom.sql`
- **Purpose:** Adds `uploaded_at` column to `ppwr_bom` table
- **Status:** Ready to execute

### 2. Models Rewritten (9 Changes)
- **Frontend:** `frontend/models.py` (4 changes)
  - ✅ PPWRBOM updated with component/subcomponent columns
  - ✅ PPWRMaterialDeclarationLink table name fixed (plural → singular)
  - ✅ SupplierDeclaration replaced with SupplierDeclarationV1
  - ✅ PPWRResult model added
  
- **Backend:** `backend/models.py` (5 changes)
  - ✅ PPWRBOM synchronized with frontend
  - ✅ PPWRMaterialDeclarationLink table name fixed
  - ✅ init_backend_db() updated for uploaded_at column
  - ✅ PPWRAssessment removed, PPWRResult added
  - ✅ SupplierDeclarationV1 added

### 3. Routes Updated (6 Changes)
- **Frontend:** `frontend/app.py` (3 changes)
  - ✅ Imports updated to use correct model names
  - ✅ /ppwr/evaluation route rewritten with direct DB query
  - ✅ _build_distinct_ppwr_declarations helper updated
  
- **Backend:** `backend/main.py` (3 changes)
  - ✅ Imports updated
  - ✅ /ppwr/assessments endpoint rewritten
  - ✅ /ppwr/evaluation/summary endpoint rewritten

### 4. Documentation Generated
- ✅ **IMPLEMENTATION_SUMMARY.md** - Technical change log
- ✅ **FRONTEND_UI_DOCUMENTATION.md** - Complete UI mockups and workflows

---

## 🚀 Execute These Commands Now

### Step 1: Run Database Migration
```bash
cd /home/gapesh/Downloads/PFAS_V0.2/frontend
python run_migrations.py
```

**Expected Output:**
```
Connecting to DB: postgresql://airadbuser:***@10.134.44.228:5432/pfasdb
Applied migration: 015_add_uploaded_at_to_ppwr_bom.sql
All migrations applied.
```

**Verification:**
```bash
psql -h 10.134.44.228 -U airadbuser -d pfasdb -c "\d ppwr_bom" | grep uploaded_at
```

Should show:
```
 uploaded_at | timestamp without time zone | | default CURRENT_TIMESTAMP
```

---

### Step 2: Restart Docker Services
```bash
cd /home/gapesh/Downloads/PFAS_V0.2
docker compose restart
```

**Expected Output:**
```
[+] Running 2/2
 ✔ Container pfas_flask     Started
 ✔ Container pfas_fastapi   Started
```

**Wait for services to be ready (~30 seconds):**
```bash
# Check Flask is up
curl -I http://localhost:5000/ | head -n 1
# Should output: HTTP/1.1 200 OK

# Check FastAPI is up
curl http://localhost:8000/docs | grep -q "FastAPI" && echo "✅ FastAPI ready"
```

---

### Step 3: Verify Dashboard Page
```bash
# Open in browser
xdg-open http://localhost:5000/
```

**What to Check:**
- ✅ Product list displays with SKU names
- ✅ **Upload timestamps visible** (from `ppwr_bom.uploaded_at`)
- ✅ Route badges show "PFAS" or "PPWR"
- ✅ Start buttons navigate to assessment pages
- ✅ No console errors in browser DevTools

**Expected View:**
```
╔═══════════════════════════════════════════╗
║  PFAS/PPWR Dashboard                      ║
╠═══════════════════════════════════════════╣
║  SKU: VET-SYRINGE-001      Route: PPWR    ║
║  📅 Uploaded: 2026-01-25 14:32 UTC       ║
║  Materials: 12 | Declarations: 8/12       ║
╚═══════════════════════════════════════════╝
```

---

### Step 4: Verify PPWR Assessment Tab
```bash
# Replace VET-SYRINGE-001 with actual SKU from your database
xdg-open http://localhost:5000/assessment/VET-SYRINGE-001?tab=ppwr
```

**What to Check:**
- ✅ Materials table displays correctly
- ✅ Declaration PDFs show clickable links
- ✅ **Upload time displayed** for each declaration
- ✅ Expansion toggle [▼] reveals supplier details
- ✅ Missing declarations show ❌ with [📤] button
- ✅ Quick Actions bar with checkboxes works
- ✅ No `AttributeError` or `NoSuchTableError` in logs

**Expected View:**
```
╔═══════════════════════════════════════════════════════╗
║  Assessment: VET-SYRINGE-001                          ║
║  ┌─────┬─────┬──────┬─────────┬─────────┐            ║
║  │ PFAS│ PPWR│ RoHS │ REACH   │ Other   │            ║
║  └─────┴─────┴──────┴─────────┴─────────┘            ║
║                                                       ║
║  ☐ A7658  📄 A7658_PETG.pdf  2.3MB  Jan 25 14:32 [▼]║
║  ☐ B7462  ❌ Missing Declaration               [📤]  ║
╚═══════════════════════════════════════════════════════╝
```

---

### Step 5: Verify Evaluation Page
```bash
xdg-open http://localhost:5000/ppwr/evaluation?sku=VET-SYRINGE-001
```

**What to Check:**
- ✅ Statistics cards display correct counts
- ✅ **Component/subcomponent columns visible**
- ✅ Chemical data displays from `ppwr_result`
- ✅ Material data displays from `ppwr_bom`
- ✅ LEFT JOIN works (shows materials without chemical data)
- ✅ Status badges color-coded correctly
- ✅ SKU filter parameter works
- ✅ No `RelationError` in logs

**Expected View:**
```
╔═══════════════════════════════════════════════════════════╗
║  PPWR Evaluation Summary - VET-SYRINGE-001                ║
╠═══════════════════════════════════════════════════════════╣
║  Total Files: 12 | Downloaded: 8 (67%)                    ║
║  Conformance: 6 (75%) | Non-Conformance: 2 (25%)         ║
║  ───────────────────────────────────────────────────────  ║
║  Component  │ Subcomp. │ Material │ CAS ID │ Status      ║
║  Syringe    │ Barrel   │ A7658    │ 24938  │ ✅ Compliant║
║  Plunger    │ Tip      │ B7346    │ 9002   │ 🔴 Non-Comp ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🧪 Testing Checklist

Run through these scenarios to ensure everything works:

### Scenario 1: Upload New BOM
1. Navigate to Dashboard: `http://localhost:5000/`
2. Click [➕ Upload BOM]
3. Select Excel file (example: `Helper_Data/BOM-1_VET SYRINGE (3).xlsx`)
4. Choose route: PPWR
5. Submit
6. **Verify:** New product appears with current timestamp in "Uploaded" field

### Scenario 2: Upload Supplier Declaration
1. Navigate to PPWR tab: `http://localhost:5000/assessment/<SKU>?tab=ppwr`
2. Find material with ❌ Missing Declaration
3. Click [📤] upload button
4. Select PDF (example: `New folder (2)/A7658_PETG.pdf`)
5. Submit
6. **Verify:** Declaration appears with upload timestamp, file link clickable

### Scenario 3: View Evaluation
1. From PPWR tab, click [🔍 View Evaluation]
2. **Verify:** Redirects to `/ppwr/evaluation?sku=<SKU>`
3. **Verify:** Component/subcomponent data populated
4. **Verify:** Chemical data from `ppwr_result` displays
5. **Verify:** Materials without chemical data show "Unknown" status

### Scenario 4: SKU Filtering
1. Navigate to: `http://localhost:5000/ppwr/evaluation` (no SKU param)
2. **Verify:** Shows all materials across all SKUs
3. Navigate to: `http://localhost:5000/ppwr/evaluation?sku=SPECIFIC-SKU`
4. **Verify:** Shows only materials for that SKU

---

## 🔍 Troubleshooting

### Issue: "column ppwr_bom.uploaded_at does not exist"
**Solution:** Migration not applied. Run:
```bash
cd frontend && python run_migrations.py
docker compose restart
```

### Issue: "relation 'ppwr_assessments' does not exist"
**Solution:** Old code still running. Verify restart:
```bash
docker ps | grep pfas
docker logs pfas_flask 2>&1 | tail -20
docker logs pfas_fastapi 2>&1 | tail -20
```

### Issue: "SupplierDeclaration has no attribute 'file_data'"
**Solution:** Code referencing old model. Check for:
```bash
cd /home/gapesh/Downloads/PFAS_V0.2/frontend
grep -n "SupplierDeclaration\.query" app.py
# Should show only lines using SupplierDeclarationV1
```

### Issue: Evaluation page shows empty table
**Solution:** No chemical data in `ppwr_result`. Verify:
```sql
psql -h 10.134.44.228 -U airadbuser -d pfasdb
SELECT COUNT(*) FROM ppwr_result;
-- If 0, run PPWR pipeline to populate data
```

### Issue: Component/subcomponent columns empty
**Solution:** BOM upload didn't include those columns. Re-upload BOM with:
- Component
- Component Description
- Subcomponent
- Subcomponent Description

---

## 📊 Database Schema Diagram

```
┌─────────────────┐
│  route          │
│─────────────────│
│ sku (PK)        │◄────┐
│ route           │     │
└─────────────────┘     │
                        │
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  ppwr_bom                   │     │  ppwr_result                 │
│─────────────────────────────│     │──────────────────────────────│
│ material_id (PK)            │────►│ material_id (PK)             │
│ sku (FK)                    │─────┤ cas_id                       │
│ product                     │     │ supplier_name                │
│ material_name               │     │ status                       │
│ supplier_name               │     │ chemical                     │
│ component                   │ NEW │ concentration                │
│ component_description       │ NEW └──────────────────────────────┘
│ subcomponent                │ NEW
│ subcomponent_description    │ NEW
│ ppwr_flag                   │
│ uploaded_at                 │ NEW
└─────────────────────────────┘
        │
        │
        ▼
┌────────────────────────────────────────┐
│  ppwr_material_declaration_link        │
│────────────────────────────────────────│
│ id (PK)                                │
│ material_id (FK → ppwr_bom)            │
│ decl_material_v1 (FK → supplier_...)   │
│ bom_material_id                        │
│ flag                                   │
│ created_at                             │
└────────────────────────────────────────┘
        │
        │
        ▼
┌────────────────────────────────────────┐
│  supplier_declaration_v1               │
│────────────────────────────────────────│
│ id (PK) INTEGER AUTOINCREMENT          │ CHANGED!
│ material_id (indexed, not PK)          │
│ material_name                          │
│ original_filename                      │
│ document_type                          │
│ file_size                              │
│ file_data (BYTEA)                      │
│ upload_date                            │
└────────────────────────────────────────┘
```

**Key Changes:**
- ✅ `ppwr_bom.uploaded_at` column added
- ✅ `ppwr_bom.component*` columns added
- ✅ `supplier_declaration_v1.id` changed from VARCHAR to INTEGER
- ✅ `ppwr_material_declaration_link` uses `decl_material_v1` (INTEGER FK)
- ✅ Table name fixed: `ppwr_material_declaration_links` → `ppwr_material_declaration_link`

---

## 📚 Documentation Files

1. **IMPLEMENTATION_SUMMARY.md** - Technical changes, SQL, testing checklist
2. **FRONTEND_UI_DOCUMENTATION.md** - Complete UI mockups, workflows, data sources
3. **NEXT_STEPS.md** (this file) - Execution guide, verification steps

---

## ✨ Success Indicators

You'll know everything is working when:

- ✅ Dashboard loads without errors
- ✅ Upload timestamps visible on product cards
- ✅ PPWR tab shows supplier declarations with upload times
- ✅ Row expansion reveals supplier campaign/name
- ✅ Evaluation page displays component/subcomponent columns
- ✅ Chemical data from `ppwr_result` appears correctly
- ✅ SKU filtering works in evaluation URL
- ✅ No `RelationError`, `NoSuchTableError`, or `NoSuchColumnError` in logs
- ✅ Console shows no JavaScript errors
- ✅ All three pages (Dashboard, PPWR Tab, Evaluation) functional

---

## 🎉 You're All Set!

The implementation is complete. Execute the steps above and verify each page loads correctly. If you encounter any issues, refer to the Troubleshooting section.

**Questions?** Check the documentation files or review server logs:
```bash
docker logs pfas_flask 2>&1 | grep -i error
docker logs pfas_fastapi 2>&1 | grep -i error
```

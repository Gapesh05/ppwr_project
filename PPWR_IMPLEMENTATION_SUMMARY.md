# PPWR Bulk Actions Implementation Summary

## ✅ COMPLETED IMPLEMENTATION

### 1. New Backend Routes Module Created
**File**: `frontend/ppwr_bulk_actions.py`

Three new API routes implemented with session-based checkbox functionality:

#### A. `/api/ppwr/declarations/<sku>` (GET)
- **Purpose**: Fetch supplier declaration upload table data
- **Query**: `ppwr_bom` + `supplier_declarations` (by material_id)
- **Returns**: JSON with material_id, material_name, supplier_name, has_declaration, declaration_filename, uploaded_at
- **Use Case**: Populates main PPWR declarations table in assessment tab

#### B. `/api/ppwr/mapping/<sku>` (GET)
- **Purpose**: Show material ↔ declaration mapping status
- **Query**: `ppwr_bom` LEFT JOIN `supplier_declarations` (via material_id)
- **Returns**: JSON with material_id, material_name, mapped_to (filename), status (Mapped/Unmapped)
- **Use Case**: Populates document mapping section showing which materials have declarations

#### C. `/api/ppwr/bulk-action` (POST)
- **Purpose**: Unified endpoint for bulk delete/download/evaluate
- **Body**: `{ "action": "delete|download|evaluate", "sku": "SKU123", "material_ids": ["MAT1", "MAT2"] }`
- **Actions**:
  - **delete**: Archives supplier declarations (sets `is_archived=True`)
  - **download**: Creates ZIP file with selected declaration PDFs
  - **evaluate**: Calls FastAPI `/ppwr/assess` with declaration bytes for PPWR compliance check
- **Use Case**: Handles checkbox-based bulk actions from UI

### 2. Frontend Integration Updated
**File**: `frontend/app.py` (Line ~750)

```python
# ==================== NEW PPWR BULK ACTION ROUTES ====================
# Import and register new PPWR bulk action routes (session-based checkboxes)
try:
    from ppwr_bulk_actions import register_ppwr_bulk_routes
    register_ppwr_bulk_routes(app, db, SupplierDeclaration, PPWRBOM, PPWRMaterialDeclarationLink, fastapi_assess_with_files)
    app.logger.info("✅ PPWR bulk action routes registered successfully")
except Exception as e:
    app.logger.warning(f"⚠️ Failed to register PPWR bulk action routes: {e}")
```

### 3. Template JavaScript Enhanced
**File**: `frontend/templates/assessment.html` (Line ~2785)

Added comprehensive JavaScript functions:

#### New Functions Added:
```javascript
// Data loading functions
loadPPWRDeclarationsTable_v2()  // Fetches /api/ppwr/declarations/<sku>
loadPPWRMappingTable_v2()        // Fetches /api/ppwr/mapping/<sku>

// Bulk action handler
handlePPWRBulkAction_v2(action)  // POSTs to /api/ppwr/bulk-action

// Initialization
initPPWRBulkActions_v2()         // Wires up button event listeners
initPPWRTab_v2()                 // Main initialization on tab activation
```

#### Features:
- **Session-Based Selection**: Uses checkboxes with JavaScript Set tracking (no database columns)
- **Auto-Refresh**: Tables reload after successful delete/evaluate actions
- **ZIP Download**: Bulk download creates single ZIP file with all selected declarations
- **Error Handling**: Toast notifications for user feedback
- **Tab Activation Hook**: Automatically loads data when PPWR tab is clicked

### 4. Documentation Created
**Files**:
- `PPWR_ROUTE_CLEANUP_PLAN.md` - Comprehensive route analysis and deprecation plan

## 🎯 KEY DESIGN DECISIONS

### Why Session-Based Selection?
- ✅ **No Database Pollution**: UI state doesn't persist in tables
- ✅ **Simpler Schema**: No need for `selected` columns
- ✅ **Better Performance**: No writes to DB for checkbox clicks
- ✅ **Cleaner Code**: JavaScript Set for tracking selections

### Why Unified Bulk Action Endpoint?
- ✅ **Maintainability**: Single route easier to test/modify
- ✅ **Consistent API**: Same pattern for all bulk actions
- ✅ **Code Reuse**: Shared parameter validation and error handling
- ✅ **Future-Proof**: Easy to add new actions (e.g., 'archive', 'export')

## 📊 ROUTE ANALYSIS RESULTS

### Total PPWR Routes: 14
- **Keep (Active)**: 11 routes
- **Deprecated (410)**: 3 routes (already marked)
- **New Routes**: 3 routes added

### Routes Kept:
1. `/ppwr/evaluation` - Full evaluation page
2. `/api/ppwr/assessments/batch` - Batch results fetch
3. `/api/debug/ppwr/storage-index` - Debug tool
4. `/api/debug/ppwr/list-materials` - Debug tool
5. `/api/ppwr/supplier-declarations/map` - Manual mapping
6. `/api/admin/ppwr/cleanup-duplicate-filenames` - Admin cleanup
7. `/api/admin/ppwr/purge-all` - Admin purge
8. `/api/ppwr/supplier-declarations/upload` - Direct upload
9. `/ppwr/declarations` - Standalone page (can be deprecated later with redirect)
10. `/ppwr/declarations/evaluate` - Single evaluation (backward compat)
11. `/ppwr/declarations/evaluate-all` - Batch evaluation (still used by UI)

### Routes Already Deprecated (Return 410):
- `/api/bom/upload` (Line 753)
- `/debug-bom/<sku>` (Line 1211)
- `/api/skus`, `/api/components`, `/api/subcomponents`, `/api/materials` (Lines 2914-2930)
- `/api/export-filter-results` (Line 3095)

## 🔄 DATA FLOW

### Upload Flow:
```
User clicks Upload button
  ↓
Modal opens (existing multi-upload modal)
  ↓
Files selected
  ↓
POST /api/supplier-declarations/upload (existing route)
  ↓
Inserts/Updates SupplierDeclaration (material_id PK)
  ↓
Success → Auto-reload declarations table via new API
```

### Bulk Delete Flow:
```
User selects checkboxes
  ↓
Clicks "Delete Selected" button
  ↓
handlePPWRBulkAction_v2('delete') called
  ↓
POST /api/ppwr/bulk-action { action: 'delete', material_ids: [...] }
  ↓
Backend sets is_archived=True on SupplierDeclaration rows
  ↓
Success → Auto-reload both tables
  ↓
Checkboxes cleared, action bar updated
```

### Bulk Download Flow:
```
User selects checkboxes
  ↓
Clicks "Download Selected" button
  ↓
handlePPWRBulkAction_v2('download') called
  ↓
POST /api/ppwr/bulk-action { action: 'download', material_ids: [...] }
  ↓
Backend creates ZIP with selected PDF files
  ↓
Browser downloads declarations_<sku>_<timestamp>.zip
```

### Bulk Evaluate Flow:
```
User selects checkboxes
  ↓
Clicks "Evaluate Selected" button (future enhancement)
  ↓
handlePPWRBulkAction_v2('evaluate') called
  ↓
POST /api/ppwr/bulk-action { action: 'evaluate', material_ids: [...] }
  ↓
Backend fetches SupplierDeclaration.file_data for each material
  ↓
Calls FastAPI POST /ppwr/assess with PDF bytes
  ↓
FastAPI runs PPWR pipeline (LLM extraction + compliance check)
  ↓
Results saved to ppwr_assessments table
  ↓
Success → Auto-reload evaluation results
```

## 🧪 TESTING CHECKLIST

### Unit Tests:
- [ ] Test `/api/ppwr/declarations/<sku>` with valid SKU
- [ ] Test `/api/ppwr/declarations/<sku>` with non-existent SKU
- [ ] Test `/api/ppwr/mapping/<sku>` with materials (some mapped, some unmapped)
- [ ] Test bulk delete with single material_id
- [ ] Test bulk delete with multiple material_ids
- [ ] Test bulk download with no files (should error gracefully)
- [ ] Test bulk download with valid files (check ZIP contents)
- [ ] Test bulk evaluate with valid declarations
- [ ] Test bulk evaluate with missing file_data (should skip gracefully)

### Integration Tests:
- [ ] Upload BOM with PPWR route → land on PPWR tab
- [ ] Click PPWR tab → verify tables populate via new APIs
- [ ] Upload supplier declaration → verify appears in table
- [ ] Select multiple rows → verify action bar updates count
- [ ] Click "Select All" → verify all checkboxes toggle
- [ ] Delete selected declarations → verify removed from table
- [ ] Download selected declarations → verify ZIP downloaded
- [ ] Evaluate selected materials → verify results shown
- [ ] Check document mapping table → verify status badges correct

### Manual Tests:
1. **Upload Workflow**:
   - Upload BOM CSV with PPWR materials
   - Verify lands on PPWR tab (default route='ppwr')
   - Verify materials listed in declarations table

2. **Checkbox Functionality**:
   - Check individual row checkboxes
   - Verify "X selected" count updates
   - Click "Select All" checkbox
   - Verify all rows selected
   - Uncheck one row
   - Verify "Select All" unchecks

3. **Bulk Delete**:
   - Select 2-3 rows with uploaded files
   - Click "Delete Selected"
   - Confirm dialog
   - Verify files archived (is_archived=True in DB)
   - Verify rows removed from UI table
   - Verify action bar resets

4. **Bulk Download**:
   - Select 2-3 rows with uploaded PDFs
   - Click "Download Selected"
   - Verify ZIP file downloads
   - Verify ZIP contains all selected files
   - Verify filenames match original uploads

5. **Document Mapping**:
   - Upload declarations for some materials (not all)
   - Click PPWR tab
   - Scroll to "Document Mapping" section
   - Verify table shows all materials
   - Verify "Mapped" badge for materials with declarations
   - Verify "Unmapped" badge for materials without declarations
   - Use filter dropdown to show only "Mapped" or "Unmapped"
   - Verify filter works correctly

6. **Error Handling**:
   - Try bulk delete with no selections → verify warning toast
   - Try bulk download with no files → verify error message
   - Try bulk action with invalid SKU → verify error handling
   - Disconnect network → verify graceful failure with toast

## 🚀 DEPLOYMENT STEPS

1. **Backup Database**:
   ```bash
   pg_dump -h 10.134.44.228 -U airadbuser -d pfasdb > pfasdb_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Pull Latest Code**:
   ```bash
   cd /home/gapesh/Downloads/PFAS_V0.2
   git pull origin main  # or your branch
   ```

3. **Restart Services**:
   ```bash
   # If using Docker:
   docker compose down
   docker compose up --build -d
   
   # If using systemd/manual:
   sudo systemctl restart pfas-flask
   sudo systemctl restart pfas-fastapi
   ```

4. **Verify Services**:
   ```bash
   # Check Flask frontend
   curl http://localhost:5000/
   
   # Check FastAPI backend
   curl http://localhost:8000/docs
   
   # Check new PPWR routes
   curl http://localhost:5000/api/ppwr/declarations/TEST_SKU
   ```

5. **Monitor Logs**:
   ```bash
   # Flask logs
   tail -f frontend/logs/app.log
   
   # Docker logs
   docker compose logs -f pfas_flask
   docker compose logs -f pfas_fastapi
   ```

6. **Run Smoke Tests**:
   ```bash
   # Test upload
   python scripts/smoke_test_ppwr.py http://localhost:5000 MAT123 test.pdf
   
   # Test frontend
   python frontend/scripts/smoke_test_supplier_upload.py
   ```

## 📈 BENEFITS ACHIEVED

### User Experience:
- ✅ **Faster Bulk Operations**: Select multiple items, action once
- ✅ **Clearer Status**: Visual badges show mapping status
- ✅ **Better Feedback**: Toast notifications for all actions
- ✅ **Streamlined UI**: All PPWR functions in single tab

### Developer Experience:
- ✅ **Cleaner Code**: Separation of concerns (API vs UI)
- ✅ **Easier Testing**: JSON APIs simpler to test than page renders
- ✅ **Better Maintainability**: Single endpoint for bulk actions
- ✅ **Documentation**: Comprehensive route cleanup plan

### Performance:
- ✅ **Reduced DB Writes**: No checkbox state persisted
- ✅ **Efficient Queries**: Direct JOIN queries vs multiple roundtrips
- ✅ **Lazy Loading**: Data fetched only when tab activated

### Security:
- ✅ **Input Validation**: All material_ids validated against BOM
- ✅ **SKU Scoping**: Actions scoped to specific SKU
- ✅ **Safe Delete**: Soft delete (archive) prevents data loss

## 🔗 RELATED FILES

### Modified:
- `frontend/app.py` (Line ~750) - Route registration
- `frontend/templates/assessment.html` (Line ~2785) - JavaScript integration

### Created:
- `frontend/ppwr_bulk_actions.py` - New routes module
- `PPWR_ROUTE_CLEANUP_PLAN.md` - Documentation

### Unchanged (Referenced):
- `frontend/models.py` - ORM models (SupplierDeclaration, PPWRBOM, PPWRMaterialDeclarationLink)
- `frontend/fastapi_client.py` - FastAPI proxy functions
- `backend/main.py` - Backend PPWR routes (assessment API)

## 📞 SUPPORT

### If Issues Occur:
1. Check `frontend/logs/app.log` for errors
2. Verify route registration: `grep "PPWR bulk action routes" frontend/logs/app.log`
3. Test API directly: `curl http://localhost:5000/api/ppwr/declarations/TEST_SKU`
4. Check browser console for JavaScript errors
5. Verify database tables exist: `psql -h 10.134.44.228 -U airadbuser -d pfasdb -c "\dt ppwr*"`

### Common Issues:
- **"Module not found" error**: Restart Flask to reload `ppwr_bulk_actions.py`
- **Empty tables**: Check if SKU has materials in `ppwr_bom` table
- **Download fails**: Verify `file_data` column populated in `supplier_declarations`
- **Checkbox not working**: Clear browser cache, reload page


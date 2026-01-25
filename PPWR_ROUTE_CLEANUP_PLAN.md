# PPWR Route Cleanup Plan

This document outlines which existing PPWR routes can be safely deprecated/removed after the new bulk action implementation.

## ✅ NEW ROUTES ADDED (Keep - Core Functionality)

1. **`/api/ppwr/declarations/<sku>` (GET)**
   - Purpose: List materials with supplier declaration status
   - Replaces: Inline table population logic
   - Status: **ADDED** - Core functionality

2. **`/api/ppwr/mapping/<sku>` (GET)**
   - Purpose: Show material ↔ declaration mapping status
   - Replaces: Old document mapping logic
   - Status: **ADDED** - Core functionality

3. **`/api/ppwr/bulk-action` (POST)**
   - Purpose: Unified endpoint for delete/download/evaluate bulk actions
   - Replaces: Multiple separate handlers
   - Status: **ADDED** - Core functionality

## 📊 EXISTING ROUTES ANALYSIS (14 Routes Reviewed)

### ✅ KEEP (8 Routes - Still Needed)

1. **`/ppwr/evaluation` (Line 107)**
   - Purpose: Full PPWR evaluation page with detailed metrics
   - Reason: Still referenced by "Evaluate" button, provides comprehensive view
   - Status: **KEEP**

2. **`/api/ppwr/assessments/batch` (Line 428)**
   - Purpose: Fetch batch assessment results for materials
   - Reason: Used by evaluation results display, not duplicated by bulk-action
   - Status: **KEEP**

3. **`/api/debug/ppwr/storage-index` (Line 459)**
   - Purpose: Debug endpoint for storage inspection
   - Reason: Useful for troubleshooting, no harm keeping
   - Status: **KEEP**

4. **`/api/debug/ppwr/list-materials` (Line 516)**
   - Purpose: Debug endpoint for material listing
   - Reason: Useful for troubleshooting
   - Status: **KEEP**

5. **`/api/ppwr/supplier-declarations/map` (Line 629)**
   - Purpose: Manual mapping of individual declarations
   - Reason: UI feature for explicit mapping, not covered by bulk actions
   - Status: **KEEP**

6. **`/api/admin/ppwr/cleanup-duplicate-filenames` (Line 699)**
   - Purpose: Admin tool to archive duplicate declarations
   - Reason: Important maintenance functionality
   - Status: **KEEP**

7. **`/api/admin/ppwr/purge-all` (Line 738)**
   - Purpose: Admin tool for hard delete of all declarations
   - Reason: Critical admin functionality
   - Status: **KEEP**

8. **`/api/ppwr/supplier-declarations/upload` (Line 1734)**
   - Purpose: Direct upload API for supplier declarations
   - Reason: Core upload functionality, still used by UI
   - Status: **KEEP**

### 🔄 OPTIONAL DEPRECATION (3 Routes - Functionality Duplicated)

9. **`/ppwr/declarations` (Line 286) - ppwr_declarations_page()**
   - Current Purpose: Standalone page for viewing/managing declarations
   - New Alternative: Integrated PPWR tab in assessment page
   - Recommendation: **DEPRECATE** - Add deprecation warning, redirect to assessment tab
   - Migration Path: Add 301 redirect to `/assessment/<sku>?tab=ppwr`

10. **`/ppwr/declarations/evaluate` (Line 311) - ppwr_declarations_evaluate()**
    - Current Purpose: Evaluate single declaration
    - New Alternative: Bulk action API with single material_id
    - Recommendation: **SOFT DEPRECATE** - Keep for backward compatibility, add warning
    - Note: Some external scripts might still use this

11. **`/ppwr/declarations/evaluate-all` (Line 364) - ppwr_declarations_evaluate_all()**
    - Current Purpose: Batch evaluate all declarations
    - New Alternative: Bulk action API with action='evaluate'
    - Recommendation: **SOFT DEPRECATE** - Keep for backward compatibility
    - Note: Still used by runPpwrEvaluateFlow() in template - could be refactored later

### ⚠️ ANALYZE BEFORE REMOVING (2 Routes - Need Investigation)

12. **`/ppwr/declarations/upload` (Line 530) - ppwr_declarations_upload_proxy()**
    - Purpose: Proxy upload endpoint (was forwarding to backend)
    - Current Status: Returns 410 Gone (storage moved to Flask)
    - Recommendation: **ALREADY DEPRECATED** - Can be safely removed
    - Note: Check if any old scripts/tests reference this

13. **`/api/ppwr/supplier-declarations/upload` (Line 1734)**
    - Purpose: Multi-file upload API
    - Status: **KEEP** - Still actively used by assessment UI

### ✅ ALREADY HANDLED (2 Routes - No Action Needed)

14. **`/static/templates/ppwr_bom_template.xlsx` (Line 3680)**
    - Purpose: Template download for BOM format
    - Status: **KEEP** - Utility route

15. **`/ppwr-assessment/<sku>` (Line 3704)**
    - Purpose: Legacy redirect (301) to unified assessment page
    - Status: **KEEP** - Provides backward compatibility

## 🎯 RECOMMENDED ACTIONS

### Phase 1: Immediate (Safe Removals)
```python
# Remove these routes - already deprecated or superseded:

# 1. Remove proxy upload route (line 530)
@app.route('/ppwr/declarations/upload', methods=['POST'])
def ppwr_declarations_upload_proxy():
    # ALREADY RETURNS 410 - can be removed entirely
```

### Phase 2: Add Deprecation Warnings (Soft Deprecation)
```python
# 2. Add redirect for standalone declarations page (line 286)
@app.route('/ppwr/declarations', methods=['GET'])
def ppwr_declarations_page():
    sku = request.args.get('sku')
    if sku:
        flash('This page has moved. Redirecting to assessment page...', 'info')
        return redirect(url_for('assessment_page', sku=sku, tab='ppwr'), code=301)
    # ... rest of old implementation with deprecation warning

# 3. Add deprecation warning to single evaluate (line 311)
@app.route('/ppwr/declarations/evaluate', methods=['POST'])
def ppwr_declarations_evaluate():
    app.logger.warning('⚠️ DEPRECATED: /ppwr/declarations/evaluate - Use /api/ppwr/bulk-action instead')
    # ... keep implementation for now

# 4. Add deprecation warning to evaluate-all (line 364)
@app.route('/ppwr/declarations/evaluate-all', methods=['POST'])
def ppwr_declarations_evaluate_all():
    app.logger.warning('⚠️ DEPRECATED: /ppwr/declarations/evaluate-all - Use /api/ppwr/bulk-action instead')
    # ... keep implementation for now
```

### Phase 3: Future Cleanup (After Testing Period)
After 1-2 weeks of monitoring:
- Remove routes with deprecation warnings if no usage logged
- Update any remaining references in tests/scripts
- Clean up template JavaScript to fully use new API

## 📝 MIGRATION CHECKLIST

- [x] Create new API routes (declarations, mapping, bulk-action)
- [x] Update template JavaScript to use new APIs
- [x] Wire up bulk action buttons
- [ ] Remove proxy upload route (line 530)
- [ ] Add deprecation warnings to evaluate routes
- [ ] Add redirect for standalone declarations page
- [ ] Test all bulk actions (delete, download, evaluate)
- [ ] Monitor logs for deprecated route usage
- [ ] Update documentation
- [ ] Remove deprecated routes after testing period

## 🔧 TESTING COMMANDS

```bash
# Test new APIs
curl -X GET "http://localhost:5000/api/ppwr/declarations/SKU123"
curl -X GET "http://localhost:5000/api/ppwr/mapping/SKU123"
curl -X POST "http://localhost:5000/api/ppwr/bulk-action" \
  -H "Content-Type: application/json" \
  -d '{"action": "delete", "sku": "SKU123", "material_ids": ["MAT1"]}'

# Check for deprecated route usage in logs
tail -f frontend/logs/app.log | grep "DEPRECATED"

# Verify redirects work
curl -I "http://localhost:5000/ppwr/declarations?sku=SKU123"
```

## 📊 IMPACT SUMMARY

- **Routes Added**: 3 new API routes
- **Routes to Remove**: 1 (proxy upload)
- **Routes to Deprecate**: 3 (with warnings)
- **Routes to Keep**: 11 (core functionality)
- **Net Change**: Cleaner API, better maintainability

## 🚀 BENEFITS OF NEW ARCHITECTURE

1. **Session-Based State**: No database pollution with UI state
2. **Unified Bulk Actions**: Single endpoint easier to maintain
3. **Clean Separation**: API routes separate from page renders
4. **Better Testing**: JSON APIs easier to test than page renders
5. **Frontend Flexibility**: JavaScript can evolve without backend changes


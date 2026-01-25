# PPWR Filename Validation Testing Guide

## Overview
This document describes how to test the new supplier declaration filename validation feature.

## Implementation Summary
✅ **Frontend validation function** added at line ~3105 in `assessment.html`
✅ **Updated openMultiUpload** function at line ~3758 with inline validation
✅ **Backend safety validation** added to `/api/supplier-declarations/upload` route in `app.py` at line ~1823
✅ **Centered toast notifications** for validation errors and success messages
✅ **Removed deprecated standalone upload form** (already commented out)

## Test Cases

### Test Case 1: Correct Format ✅
**Filename:** `A8362_Silicone_Rubber.pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ✅ Upload succeeds
**Expected Toast:** Green toast: "✅ Successfully uploaded: A8362_Silicone_Rubber.pdf"

### Test Case 2: Material ID Mismatch ❌
**Filename:** `A8363_Silicone_Rubber.pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ❌ Upload blocked
**Expected Toast:** Red toast with message:
```
Upload Unsuccessful

Material ID mismatch
Expected: A8362
Got: A8363

Please rename file to:
A8362_Silicone Rubber.pdf
```

### Test Case 3: Material Name Mismatch ❌
**Filename:** `A8362_Steel.pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ❌ Upload blocked
**Expected Toast:** Red toast with message:
```
Upload Unsuccessful

Material Name mismatch
Expected: Silicone Rubber
Got: Steel

Please rename file to:
A8362_Silicone Rubber.pdf
```

### Test Case 4: No Underscore (Invalid Format) ❌
**Filename:** `A8362SiliconeRubber.pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ❌ Upload blocked
**Expected Toast:** Red toast with message:
```
Upload Unsuccessful

Filename must follow format:
A8362_Silicone Rubber.pdf
```

### Test Case 5: Multiple Underscores (Partial Match) ✅
**Filename:** `A8362_Silicone_Rubber_Material.pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ✅ Upload succeeds (partial match)
**Expected Toast:** Green toast: "✅ Successfully uploaded: A8362_Silicone_Rubber_Material.pdf"

### Test Case 6: Case Insensitive ✅
**Filename:** `a8362_silicone_rubber.pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ✅ Upload succeeds (case-insensitive)
**Expected Toast:** Green toast: "✅ Successfully uploaded: a8362_silicone_rubber.pdf"

### Test Case 7: Special Characters in Name ✅
**Filename:** `A8362_Silicone-Rubber(High_Grade).pdf`
**Expected Material ID:** `A8362`
**Expected Material Name:** `Silicone Rubber`
**Expected Result:** ✅ Upload succeeds (partial match)
**Expected Toast:** Green toast: "✅ Successfully uploaded: A8362_Silicone-Rubber(High_Grade).pdf"

### Test Case 8: Backend Safety Net (Frontend Bypassed)
If frontend validation is somehow bypassed, backend will catch it:
**Backend Validation Rules:**
- Checks if BOM row exists for SKU + material_id
- Validates filename starts with `material_id_`
- Validates filename contains material_name (case-insensitive)
**Response on Failure:**
```json
{
  "success": false,
  "errors": [{
    "filename": "Wrong_File.pdf",
    "error": "Filename must start with 'A8362_'. Expected format: A8362_Silicone Rubber.pdf"
  }]
}
```

## Manual Testing Steps

1. **Navigate to PPWR Assessment Page**
   ```
   http://localhost:5000/assessment/SKU_VALUE?tab=ppwr
   ```

2. **Locate Material Row**
   - Find a material row without a declaration (no ✓ icon)
   - Note the Material ID (e.g., `A8362`)
   - Note the Material Name in gray text below the ID

3. **Click Upload Button**
   - Click the blue "Upload" button for that row
   - File picker dialog should open

4. **Test Invalid Filename**
   - Select a file with wrong material ID (e.g., `A8363_Silicone_Rubber.pdf`)
   - **Expected:** Red centered toast appears with specific error message
   - **Expected:** File picker closes, NO upload happens
   - **Expected:** Table does NOT refresh

5. **Test Valid Filename**
   - Click Upload button again
   - Select file with correct format (e.g., `A8362_Silicone_Rubber.pdf`)
   - **Expected:** File uploads immediately (no modal)
   - **Expected:** Green centered toast: "✅ Successfully uploaded: A8362_Silicone_Rubber.pdf"
   - **Expected:** After 1.5 seconds, table refreshes showing the new file
   - **Expected:** Upload button replaced with ✓ icon and Download button

6. **Verify Backend Validation**
   - Use browser DevTools Network tab
   - Monitor POST request to `/api/supplier-declarations/upload`
   - Upload invalid filename
   - **Expected:** Response 200 with `success: false` and error details

## Validation Flow Diagram

```
User Clicks Upload Button
       ↓
File Picker Opens
       ↓
User Selects File
       ↓
validatePPWRFilename(file, materialId, materialName)
       ↓
   [Valid?]
       ↓
    ✅ YES → POST /api/supplier-declarations/upload
       ↓          ↓
       |     Backend validates:
       |     - BOM row exists
       |     - Filename starts with materialId_
       |     - Filename contains materialName
       |          ↓
       |      [Valid?]
       |          ↓
       |       ✅ YES → Store in DB
       |          ↓
       |     Return success JSON
       |          ↓
       ←──────────┘
       ↓
Show green toast
       ↓
Refresh table (1.5s delay)
       ↓
Complete
       
    ❌ NO (Frontend) → Show red toast
       ↓
Stop (no upload)
       ↓
Complete

    ❌ NO (Backend) → Return error JSON
       ↓
Show red toast
       ↓
Complete
```

## Files Modified

### Frontend
**File:** `frontend/templates/assessment.html`
- **Line ~3105:** Added `validatePPWRFilename()` function (55 lines)
- **Line ~3758:** Updated `openMultiUpload()` to validate before upload (70+ lines changed)
- **Line ~3159:** Enhanced `showCenteredToast()` (already existed, unchanged)

### Backend
**File:** `frontend/app.py`
- **Line ~1823:** Added filename validation to `/api/supplier-declarations/upload` route
  - Checks BOM row exists (`PPWRBOM` table)
  - Validates filename starts with `material_id_`
  - Validates filename contains `material_name`
  - Returns descriptive error if validation fails

## Expected User Experience

### Before Validation (Old Flow)
1. User clicks Upload
2. Modal or file picker opens
3. User selects **any filename**
4. File uploads regardless of filename
5. ⚠️ **Problem:** Could upload `WrongFile.pdf` for material `A8362_Silicone_Rubber`

### After Validation (New Flow)
1. User clicks Upload
2. File picker opens directly (no modal)
3. User selects file
4. **Validation runs immediately:**
   - ✅ If valid: Upload starts, green toast appears
   - ❌ If invalid: Red toast shows exact error, upload blocked
5. ✅ **Result:** Only correctly named files can be uploaded

## Toast Notification Styling

### Success Toast (Green)
```html
<div class="toast bg-success text-white">
  <div class="toast-body">
    <strong>✅ Successfully uploaded:<br>A8362_Silicone_Rubber.pdf</strong>
  </div>
</div>
```
- **Position:** Center screen
- **Auto-dismiss:** 5 seconds
- **Background:** Green (#198754)
- **Text:** White

### Error Toast (Red)
```html
<div class="toast bg-danger text-white">
  <div class="toast-body">
    <strong>Upload Unsuccessful<br><br>Material ID mismatch<br>Expected: A8362<br>Got: A8363<br><br>Please rename file to:<br>A8362_Silicone Rubber.pdf</strong>
  </div>
</div>
```
- **Position:** Center screen
- **Auto-dismiss:** 5 seconds
- **Background:** Red (#dc3545)
- **Text:** White, line breaks for readability

## Debugging Tips

### Check Validation Function
Open browser console and run:
```javascript
// Test validation function directly
const testFile = new File(["test"], "A8362_Silicone_Rubber.pdf", {type: "application/pdf"});
const result = validatePPWRFilename(testFile, "A8362", "Silicone Rubber");
console.log("Validation result:", result);
// Expected: {valid: true}

const invalidFile = new File(["test"], "A8363_Steel.pdf", {type: "application/pdf"});
const result2 = validatePPWRFilename(invalidFile, "A8362", "Silicone Rubber");
console.log("Validation result (invalid):", result2);
// Expected: {valid: false, reason: "material_id_mismatch", message: "..."}
```

### Check Backend Validation
Use curl or Postman:
```bash
# Test backend validation
curl -X POST http://localhost:5000/api/supplier-declarations/upload \
  -F "files=@WrongFile.pdf" \
  -F "sku=TEST_SKU" \
  -F "material=A8362"

# Expected response:
# {
#   "success": false,
#   "errors": [{
#     "filename": "WrongFile.pdf",
#     "error": "Filename must start with 'A8362_'. Expected format: A8362_Silicone Rubber.pdf"
#   }]
# }
```

### Check Toast Container
Open browser console:
```javascript
// Check if toast container exists
const container = document.getElementById('centerToastContainer');
console.log("Toast container:", container);

// Test toast manually
showCenteredToast('Test error message', 'error');
showCenteredToast('Test success message', 'success');
```

## Success Criteria

✅ Frontend validation blocks incorrect filenames before upload
✅ Backend validation catches any bypassed frontend validation
✅ Centered toast shows specific error messages with expected filename
✅ Success toast appears after successful upload
✅ Table refreshes automatically after upload
✅ No deprecated upload forms or modals remain
✅ Validation is case-insensitive
✅ Partial name matching works for long material names
✅ Upload button replaced with ✓ and Download after successful upload

## Known Limitations

1. **Partial name matching** - If material name is "Steel" and user uploads "Steel_Grade_A", it will pass (partial match accepted)
2. **Case insensitivity** - `a8362_silicone.pdf` matches `A8362_Silicone` (intentional for user convenience)
3. **Multiple underscores** - Filename can have more underscores after the first one (e.g., `A8362_Silicone_High_Grade.pdf`)

## Rollback Instructions

If validation causes issues, temporarily disable by commenting out validation call:

```javascript
// In openMultiUpload function, comment out validation:
/*
const validation = validatePPWRFilename(file, mu_state.rowMaterial, materialName);
if (!validation.valid) {
  showCenteredToast(validation.message, 'error');
  return;
}
*/
```

Or revert commits:
```bash
git log --oneline | head -5  # Find commit hash
git revert <commit_hash>
```

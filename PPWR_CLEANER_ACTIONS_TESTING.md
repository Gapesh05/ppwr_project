# PPWR Cleaner Actions Column - Testing Checklist

## Pre-Test Setup
- [ ] Restart Flask frontend: `docker compose restart pfas_flask` (or `python frontend/app.py`)
- [ ] Clear browser cache and reload page
- [ ] Navigate to PPWR assessment page with active SKU
- [ ] Open browser DevTools Console (F12) to monitor for errors

## Table Structure Tests

### Column Layout
- [ ] Verify table shows exactly 6 columns:
  1. Checkbox
  2. Material (ID + name)
  3. Supplier
  4. Declaration (PDF link or "Not uploaded")
  5. Uploaded At (timestamp or dash)
  6. Actions (Details or Upload button)
- [ ] Verify empty state message uses colspan="6"
- [ ] No console errors on page load

### Declaration Column Display
- [ ] **Materials WITH declarations:**
  - [ ] Shows red PDF icon
  - [ ] Shows clickable filename link (blue, underlined on hover)
  - [ ] Shows file size in KB below filename
  - [ ] Shows upload timestamp with clock icon
  - [ ] Clicking link downloads PDF in new tab
  
- [ ] **Materials WITHOUT declarations:**
  - [ ] Shows warning icon with "Not uploaded" text
  - [ ] Text is gray and italicized
  - [ ] No clickable elements

### Actions Column Display
- [ ] **Materials WITH declarations:**
  - [ ] Shows "Details" button with chevron-down icon
  - [ ] Button is outlined blue (btn-outline-primary)
  - [ ] Button has proper title attribute
  - [ ] No Upload/Delete/Download buttons visible
  
- [ ] **Materials WITHOUT declarations:**
  - [ ] Shows "Upload" button in primary blue
  - [ ] Button has upload icon
  - [ ] Clicking opens file upload dialog (existing functionality)

## Expansion Toggle Tests

### Opening Expansion
- [ ] Click "Details" button on first material
- [ ] **Verify expansion row appears:**
  - [ ] Light gray background
  - [ ] White card with shadow
  - [ ] colspan="6" (spans all columns)
  - [ ] No layout shift or overflow issues
- [ ] **Verify card content:**
  - [ ] Shows "Material Details: [Material ID]" header with info icon
  - [ ] Shows "Supplier Campaign" label with badge
  - [ ] Badge is green if Active, yellow if Not Assigned
  - [ ] Shows "Supplier Name" label with supplier value
  - [ ] NO Material Name shown (removed as redundant)
  - [ ] NO Declaration Status shown (removed as redundant)
- [ ] **Verify visual feedback:**
  - [ ] Chevron icon changes from down (▼) to up (▲)
  - [ ] Button remains clickable

### Closing Expansion
- [ ] Click "Details" button again (on same material)
- [ ] Expansion row disappears smoothly
- [ ] Chevron icon changes back from up (▲) to down (▼)
- [ ] No console errors

### Multiple Expansions
- [ ] Open expansion for Material A
- [ ] Open expansion for Material B (while A is still open)
- [ ] **Verify both expansions visible simultaneously:**
  - [ ] Material A expansion still visible
  - [ ] Material B expansion visible below its row
  - [ ] Both chevrons show up (▲) state
- [ ] Close Material A expansion
- [ ] Verify Material B expansion remains open
- [ ] Close Material B expansion
- [ ] Verify all expansions closed cleanly

## Backend API Tests

### Success Case
- [ ] Open browser DevTools Network tab
- [ ] Click "Details" button
- [ ] **Verify API call:**
  - [ ] Request URL: `/api/ppwr/material-details/[material_id]`
  - [ ] Method: GET
  - [ ] Status: 200 OK
- [ ] **Verify response JSON:**
  ```json
  {
    "success": true,
    "material_id": "A7658",
    "supplier_name": "Acme Corp",
    "supplier_campaign": "Active",
    "material_name": "PETG",
    "has_declaration": true
  }
  ```

### Error Cases
- [ ] **Material not in PPWR BOM:**
  - [ ] Manually trigger API: `/api/ppwr/material-details/INVALID_ID`
  - [ ] Verify 404 status
  - [ ] Verify error message: "Material INVALID_ID not found in PPWR BOM"
  
- [ ] **Network error simulation:**
  - [ ] Disconnect network (or use DevTools throttling)
  - [ ] Click "Details" button
  - [ ] Verify toast notification: "Failed to load material details"
  - [ ] No JavaScript console errors
  - [ ] Button remains functional after reconnection

## Bulk Operations Integration

### Select All with Expansions
- [ ] Open expansion rows for 2 materials
- [ ] Click "Select All" checkbox
- [ ] Verify all checkboxes checked (including rows with expansions)
- [ ] Expansion rows remain visible
- [ ] Click "Select All" again to deselect
- [ ] Verify all checkboxes unchecked
- [ ] Expansion rows still visible (not affected by selection)

### Bulk Download
- [ ] Select 3 materials with declarations
- [ ] Open expansion for one selected material
- [ ] Click "Download Selected" button
- [ ] Verify download happens successfully
- [ ] Verify expansion remains open during download
- [ ] Verify checkboxes cleared after download

### Bulk Delete
- [ ] Select 2 materials with declarations
- [ ] Open expansion for one selected material
- [ ] Click "Delete Selected" button
- [ ] Confirm deletion in prompt
- [ ] Verify materials removed from table
- [ ] Verify expansion rows removed along with parent rows
- [ ] Verify checkboxes cleared after deletion

### Bulk Evaluate
- [ ] Select multiple materials
- [ ] Open expansions for some selected materials
- [ ] Click "Evaluate Selected" button
- [ ] Verify evaluation triggers (check backend logs)
- [ ] Verify expansions remain after evaluation completes

## Upload Flow Integration

### Upload → Details Transition
- [ ] Find material with "Not uploaded" status
- [ ] Verify "Upload" button shown in Actions column
- [ ] Click "Upload" button
- [ ] Upload a test PDF file
- [ ] **After upload completes:**
  - [ ] Declaration column updates with PDF link
  - [ ] File size and timestamp appear
  - [ ] Actions button changes from "Upload" to "Details"
  - [ ] Checkbox becomes enabled (was disabled before)
- [ ] Click new "Details" button
- [ ] Verify expansion opens with supplier info

## Edge Cases & Error Handling

### Empty Expansion Fields
- [ ] Click Details on material with no supplier name in DB
- [ ] Verify expansion shows:
  - [ ] Supplier Campaign: "Not Assigned" (yellow badge)
  - [ ] Supplier Name: "—" (em dash)
- [ ] No "null" or "undefined" text visible

### Rapid Toggle Clicks
- [ ] Click Details button rapidly 5 times
- [ ] Verify smooth open/close behavior
- [ ] No duplicate expansion rows created
- [ ] No console errors or race conditions

### Long Material IDs
- [ ] Test with material ID > 20 characters
- [ ] Verify expansion card handles long IDs gracefully
- [ ] No text overflow or layout breaks

### Special Characters in Supplier Name
- [ ] Test with supplier name containing: & < > " ' /
- [ ] Verify proper HTML escaping in expansion card
- [ ] No XSS vulnerabilities

## Cross-Browser Testing
- [ ] **Chrome/Edge:** All tests pass
- [ ] **Firefox:** All tests pass
- [ ] **Safari:** All tests pass (if available)
- [ ] **Mobile Safari:** Touch interaction works
- [ ] **Mobile Chrome:** Touch interaction works

## Performance Tests
- [ ] Load SKU with 50+ materials
- [ ] Open/close 10 expansions rapidly
- [ ] Verify smooth performance (no lag)
- [ ] No memory leaks (check DevTools Memory tab)

## Accessibility Tests
- [ ] **Keyboard Navigation:**
  - [ ] Tab through table rows
  - [ ] Space/Enter key opens Details button
  - [ ] Tab moves focus through expansion card elements
  - [ ] Escape key closes expansion (if implemented)
  
- [ ] **Screen Reader:**
  - [ ] Enable screen reader (NVDA/JAWS/VoiceOver)
  - [ ] Navigate to Details button
  - [ ] Verify button announces as "Details button" with state
  - [ ] Verify expansion content is read correctly
  
- [ ] **Color Contrast:**
  - [ ] Run axe DevTools accessibility scan
  - [ ] Verify no contrast violations
  - [ ] Badge colors meet WCAG AA standards

## Regression Tests (Ensure No Breaks)
- [ ] Select All checkbox still works
- [ ] Indeterminate state still shows correctly
- [ ] Bulk action buttons enable/disable properly
- [ ] PPWR mapping table loads correctly
- [ ] Other tabs (PFAS, RoHS, REACH) unaffected
- [ ] Dashboard product list unaffected
- [ ] BOM upload still works

## Documentation Verification
- [ ] Implementation summary document created: `PPWR_CLEANER_ACTIONS_IMPLEMENTATION.md`
- [ ] Visual guide document created: `PPWR_CLEANER_ACTIONS_VISUAL_GUIDE.md`
- [ ] Testing checklist document created: `PPWR_CLEANER_ACTIONS_TESTING.md`
- [ ] All documents match actual implementation

## Sign-Off
- [ ] All critical tests passed
- [ ] No console errors
- [ ] No visual regressions
- [ ] Performance acceptable
- [ ] Accessibility compliant
- [ ] Ready for production

---

## Test Results Summary

**Date:** _______________
**Tester:** _______________
**Browser:** _______________
**OS:** _______________

**Total Tests:** _____ / _____
**Passed:** _____ 
**Failed:** _____
**Skipped:** _____

**Critical Issues Found:**
1. _________________________________________________
2. _________________________________________________
3. _________________________________________________

**Notes:**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**Recommendation:** ☐ PASS   ☐ FAIL   ☐ CONDITIONAL PASS

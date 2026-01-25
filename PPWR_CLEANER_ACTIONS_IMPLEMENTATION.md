# PPWR Cleaner Actions Column - Implementation Summary

## Overview
Implemented a cleaner PPWR tab design with:
- **Actions column exclusively for row expansion toggle** (no individual delete/download buttons)
- **Simplified expansion row showing only Supplier Campaign and Supplier Name**
- **All delete/download operations via bulk action buttons**

## Changes Made

### 1. Frontend: Updated Table Row Generation
**File:** `frontend/templates/assessment.html`
**Function:** `loadPPWRDeclarationsTable_v2()` (line 2936)

**Key Changes:**
- ✅ **Column 4 (Declaration):** Changed from upload button to clickable PDF filename link
  - Shows file icon, filename, file size, and upload timestamp for uploaded declarations
  - Shows "Not uploaded" message for materials without declarations
  - Uses `/api/supplier-declarations/download/${materialId}` for downloads
  
- ✅ **Column 5 (Actions):** Simplified to show only expansion toggle
  - Shows **"Details"** button with chevron-down icon for materials with declarations
  - Shows **"Upload"** button for materials without declarations
  - Calls `toggleRowDetails('${materialId}')` when clicked
  - No individual delete/download buttons (use bulk actions instead)

- ✅ **Empty State:** Updated colspan from 5 to 6

**Before:**
```javascript
<button class="btn btn-sm ${row.has_declaration ? 'btn-success' : 'btn-outline-secondary'}">
  <i class="bi ${row.has_declaration ? 'bi-check-circle' : 'bi-upload'}"></i>
  ${row.has_declaration ? row.declaration_filename : 'Upload'}
</button>
```

**After:**
```javascript
// Column 4 - Declaration with clickable PDF link
${hasDeclaration ? `
  <div>
    <a href="/api/supplier-declarations/download/${materialId}" class="text-decoration-none" target="_blank">
      <i class="bi bi-file-earmark-pdf text-danger"></i> ${row.declaration_filename || row.original_filename}
    </a>
    ${row.file_size ? `<br><small class="text-muted">${(row.file_size / 1024).toFixed(1)} KB</small>` : ''}
  </div>
  ${uploadTime ? `<div class="small text-muted mt-1"><i class="bi bi-clock"></i> ${uploadTime}</div>` : ''}
` : `
  <span class="text-muted fst-italic"><i class="bi bi-exclamation-circle text-warning"></i> Not uploaded</span>
`}

// Column 5 - Actions with only expansion toggle
${hasDeclaration ? `
  <button class="btn btn-sm btn-outline-primary" onclick="toggleRowDetails('${materialId}')" title="Show details">
    <i class="bi bi-chevron-down"></i> Details
  </button>
` : `
  <button class="btn btn-sm btn-primary" data-action="upload" data-material="${materialId}" title="Upload file">
    <i class="bi bi-upload"></i> Upload
  </button>
`}
```

### 2. Frontend: Added Expansion Toggle Function
**File:** `frontend/templates/assessment.html`
**Function:** `toggleRowDetails(materialId)` (after line 3120)

**Features:**
- ✅ **Toggle Behavior:** Click to open expansion, click again to close
- ✅ **Visual Feedback:** Changes chevron icon from down (▼) to up (▲)
- ✅ **Clean Display:** Shows only Supplier Campaign and Supplier Name
- ✅ **Inline Card Layout:** Uses Bootstrap card with shadow for professional appearance
- ✅ **Status Badge:** Shows "Active" (green) or "Not Assigned" (yellow) for supplier campaign
- ✅ **Error Handling:** Shows toast notification on fetch errors

**Implementation:**
```javascript
function toggleRowDetails(materialId) {
  const existingDetailsRow = document.getElementById(`details-${materialId}`);
  
  if (existingDetailsRow) {
    // Close if already open
    existingDetailsRow.remove();
    // Change icon back to down
    const btn = document.querySelector(`button[onclick="toggleRowDetails('${materialId}')"]`);
    if (btn) {
      btn.querySelector('i').className = 'bi bi-chevron-down';
    }
    return;
  }
  
  // Fetch material details from backend
  fetch(`/api/ppwr/material-details/${encodeURIComponent(materialId)}`)
    .then(resp => resp.json())
    .then(data => {
      if (!data.success) {
        mu_toast(data.error || 'Failed to fetch material details', 'PPWR', 'danger', 3000);
        return;
      }
      
      // Create expansion row with colspan=6
      const detailsRow = document.createElement('tr');
      detailsRow.id = `details-${materialId}`;
      detailsRow.className = 'bg-light';
      detailsRow.innerHTML = `
        <td colspan="6" class="p-3">
          <div class="card border-0 shadow-sm">
            <div class="card-body">
              <h6 class="card-title mb-3">
                <i class="bi bi-info-circle text-primary"></i>
                Material Details: <strong>${materialId}</strong>
              </h6>
              <div class="row">
                <div class="col-md-6">
                  <p class="mb-2">
                    <strong>Supplier Campaign:</strong> 
                    <span class="badge ${data.supplier_campaign ? 'bg-success' : 'bg-warning text-dark'}">
                      ${data.supplier_campaign || 'Not Assigned'}
                    </span>
                  </p>
                </div>
                <div class="col-md-6">
                  <p class="mb-2">
                    <strong>Supplier Name:</strong> 
                    <span class="text-dark">${data.supplier_name || '—'}</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </td>
      `;
      
      // Insert after parent row
      parentRow.after(detailsRow);
      
      // Change icon to up
      const btn = document.querySelector(`button[onclick="toggleRowDetails('${materialId}')"]`);
      if (btn) {
        btn.querySelector('i').className = 'bi bi-chevron-up';
      }
    })
    .catch(error => {
      console.error('Error fetching material details:', error);
      mu_toast('Failed to load material details', 'PPWR', 'danger', 3000);
    });
}
```

### 3. Backend: Material Details API Route
**File:** `frontend/app.py`
**Route:** `GET /api/ppwr/material-details/<material_id>`

**Functionality:**
- ✅ **Queries PPWR BOM table** for material details
- ✅ **Checks Supplier Declaration table** for campaign status
- ✅ **Returns JSON response** with supplier info
- ✅ **Error Handling:** Returns 404 if material not found, 500 on exceptions

**Implementation:**
```python
@app.route('/api/ppwr/material-details/<material_id>', methods=['GET'])
def api_ppwr_material_details(material_id):
    """Fetch supplier campaign and supplier name for material details expansion.
    
    Returns:
        JSON with success, material_id, supplier_name, supplier_campaign
    """
    try:
        app.logger.info(f"Fetching material details for: {material_id}")
        
        # Query PPWR BOM table for material details
        bom_row = db.session.query(PPWRBOM).filter_by(material_id=material_id).first()
        
        if not bom_row:
            return jsonify({
                'success': False,
                'error': f'Material {material_id} not found in PPWR BOM'
            }), 404
        
        # Check if supplier declaration exists (determines campaign status)
        decl = SupplierDeclaration.query.filter_by(material_id=material_id).first()
        has_declaration = decl is not None and not getattr(decl, 'is_archived', False)
        
        # Determine supplier campaign status
        supplier_campaign = 'Active' if has_declaration else None
        
        return jsonify({
            'success': True,
            'material_id': material_id,
            'supplier_name': bom_row.supplier_name or '—',
            'supplier_campaign': supplier_campaign,
            'material_name': bom_row.material_name,  # Sent but not displayed in UI
            'has_declaration': has_declaration  # Sent but not displayed in UI
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error fetching material details for {material_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**Response Format:**
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

## Design Decisions

### 1. Actions Column Purpose
**Decision:** Actions column exclusively for row expansion toggle
**Rationale:** 
- Cleaner UI with single-purpose columns
- Reduces visual clutter
- All bulk operations consolidated in action bar

### 2. Expansion Row Content
**Decision:** Show only Supplier Campaign and Supplier Name
**Rationale:**
- Material Name already visible in Material column
- Declaration Status already visible in Declaration column
- Avoids redundant information
- Focuses on key supplier information

### 3. Delete/Download Operations
**Decision:** All delete/download via bulk action buttons
**Rationale:**
- Multi-row operations more efficient
- Consistent with Select All checkbox functionality
- Reduces duplicate UI elements
- Better workflow for managing multiple declarations

### 4. Toggle Function Behavior
**Decision:** Click to open, click again to close (toggle)
**Rationale:**
- Intuitive user experience
- Visual feedback via icon change (▼ → ▲)
- Allows multiple expansions simultaneously
- No need for separate close button

## UI Flow

### Normal Flow (Material with Declaration)
1. User sees table row with clickable PDF filename
2. User clicks **"Details"** button with chevron-down icon
3. Expansion row appears below with supplier details
4. Icon changes to chevron-up
5. User can click again to close expansion

### Upload Flow (Material without Declaration)
1. User sees "Not uploaded" message in Declaration column
2. User clicks **"Upload"** button in Actions column
3. File upload dialog appears (existing functionality)
4. After upload, button changes to **"Details"** toggle

### Bulk Operations Flow
1. User selects multiple materials using checkboxes
2. User clicks **Download Selected** or **Delete Selected** in action bar
3. Operation applies to all selected materials
4. No individual action buttons needed in table

## Testing Checklist

- [ ] Navigate to PPWR tab with active SKU
- [ ] Verify table shows 6 columns (Checkbox, Material, Supplier, Declaration, Uploaded At, Actions)
- [ ] Verify Declaration column shows clickable PDF links for uploaded materials
- [ ] Click Details button to open expansion row
- [ ] Verify expansion shows only Supplier Campaign and Supplier Name
- [ ] Verify chevron icon changes from down to up
- [ ] Click Details button again to verify expansion closes
- [ ] Verify chevron icon changes back to down
- [ ] Test with material that has no declaration (should show Upload button)
- [ ] Test Select All checkbox with expansion rows open
- [ ] Test bulk download with multiple materials selected
- [ ] Test bulk delete with multiple materials selected
- [ ] Verify empty state shows "No materials found" with colspan=6

## Related Files

### Modified Files:
- `frontend/templates/assessment.html` - Updated table generation and added toggle function
- `frontend/app.py` - Added material details API route

### Related Documentation:
- `PPWR_SELECT_ALL_IMPLEMENTATION.md` - Select All checkbox implementation
- `PPWR_SELECT_ALL_VISUAL_GUIDE.md` - Visual guide with diagrams

## Benefits

1. **Cleaner UI:** Single-purpose Actions column reduces visual clutter
2. **Consistent UX:** All bulk operations in one place
3. **Better Information Architecture:** Expansion row shows only non-redundant data
4. **Improved Workflow:** Multi-row operations more efficient than individual actions
5. **Professional Appearance:** Inline card layout with badges and icons
6. **Intuitive Interaction:** Toggle behavior with visual feedback

## Notes

- Expansion rows use `colspan="6"` to span all table columns
- Each expansion row has unique ID: `details-${materialId}`
- Toggle function uses `querySelector` to find parent row
- Backend route queries PPWR BOM table first, then checks declarations
- Supplier campaign shows "Active" if declaration exists, else "Not Assigned"
- All error states handled with toast notifications

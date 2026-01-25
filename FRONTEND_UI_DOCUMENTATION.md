# 🖥️ Frontend UI Documentation - PFAS/PPWR Application

## 📄 PAGE 1: Dashboard (`/`)

### Purpose
Main landing page showing all products grouped by SKU with their assessment routes and upload timestamps.

### UI Layout

```
╔════════════════════════════════════════════════════════════════════════════╗
║  PFAS/PPWR Dashboard                                    [User: Admin] [⚙️]  ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  📊 Products Overview                                  [➕ Upload BOM]     ║
║  ──────────────────────────────────────────────────────────────────────    ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │ SKU: VET-SYRINGE-001                        Route: PPWR     [▶ Start]│ ║
║  │ Product: Veterinary Syringe Assembly                                 │ ║
║  │ 📅 Uploaded: 2026-01-25 14:32 UTC                                    │ ║
║  │ ───────────────────────────────────────────────────────────────────  │ ║
║  │ Materials: 12  |  Declarations: 8/12  |  Status: ⚠️ In Progress      │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │ SKU: PACK-BOX-5530                          Route: PFAS     [▶ Start]│ ║
║  │ Product: Corrugated Packaging Box 5530                               │ ║
║  │ 📅 Uploaded: 2026-01-24 09:15 UTC                                    │ ║
║  │ ───────────────────────────────────────────────────────────────────  │ ║
║  │ Materials: 5   |  Declarations: 5/5   |  Status: ✅ Complete         │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │ SKU: LAB-TUBE-A7658                         Route: PPWR     [▶ Start]│ ║
║  │ Product: Laboratory Sample Tube                                      │ ║
║  │ 📅 Uploaded: 2026-01-23 16:48 UTC                                    │ ║
║  │ ───────────────────────────────────────────────────────────────────  │ ║
║  │ Materials: 8   |  Declarations: 3/8   |  Status: 🔴 Missing Files    │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  [1] [2] [3] ... [10]                           Showing 1-3 of 28 products║
╚════════════════════════════════════════════════════════════════════════════╝
```

### Key Features
- **Upload Timestamp Display:** Shows when each product BOM was uploaded (from `ppwr_bom.uploaded_at`)
- **Route Badge:** Displays whether product uses PFAS or PPWR assessment
- **Progress Tracking:** Shows how many declarations uploaded vs total materials
- **Status Indicators:**
  - ✅ Complete: All materials have declarations
  - ⚠️ In Progress: Some declarations missing
  - 🔴 Missing Files: Many declarations missing
- **Quick Actions:** "Start" button routes to appropriate assessment page

### Data Source
```sql
SELECT DISTINCT 
    ppwr_bom.sku,
    route.route,
    MAX(ppwr_bom.uploaded_at) as uploaded_at
FROM ppwr_bom
LEFT JOIN route ON ppwr_bom.sku = route.sku
GROUP BY ppwr_bom.sku, route.route
ORDER BY uploaded_at DESC;
```

---

## 📄 PAGE 2: PPWR Assessment Tab (`/assessment/<sku>?tab=ppwr`)

### Purpose
Manage supplier declarations for a specific product's materials. Upload PDFs, map declarations to materials, view evaluation.

### UI Layout

```
╔════════════════════════════════════════════════════════════════════════════╗
║  Assessment: VET-SYRINGE-001                             [← Back to Home]  ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌─────────┬─────────┬─────────┬─────────┬─────────┐                     ║
║  │  PFAS   │  PPWR*  │  RoHS   │  REACH  │  Other  │                     ║
║  └─────────┴─────────┴─────────┴─────────┴─────────┘                     ║
║                                                                            ║
║  ═══════════════════════════════════════════════════════════════════════  ║
║  🔵 PPWR Tab - Packaging & Packaging Waste Regulation                     ║
║  ═══════════════════════════════════════════════════════════════════════  ║
║                                                                            ║
║  📁 Supplier Declarations                        [🔍 View Evaluation]     ║
║  ──────────────────────────────────────────────────────────────────────   ║
║                                                                            ║
║  Quick Actions:  [☑️ Select All] [📤 Upload Selected] [🗑️ Archive]        ║
║                                                                            ║
║  ┌────────────────────────────────────────────────────────────────────┐  ║
║  │ ☐  Material      Declaration File       Size    Upload Time  Actions│  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ ☐  A7658         📄 A7658_PETG.pdf      2.3 MB  Jan 25 14:32  [▼]  │  ║
║  │                                                                      │  ║
║  │    ➜ Supplier Campaign: Active                                      │  ║
║  │    ➜ Supplier Name: PlasticTech Inc.                                │  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ ☐  A8362         📄 A8362_Tyvek.pdf     1.8 MB  Jan 25 14:31  [▼]  │  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ ☐  B7346         📄 B7346_PE.pdf        1.5 MB  Jan 25 14:30  [▼]  │  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ ☐  B7462         ❌ Missing Declaration                      [📤]   │  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ ☐  C7236         📄 C7236_PP_Film.pdf   2.1 MB  Jan 25 14:28  [▼]  │  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ ☐  C9347         ❌ Missing Declaration                      [📤]   │  ║
║  └────────────────────────────────────────────────────────────────────┘  ║
║                                                                            ║
║  📋 Material → Declaration Mapping                                        ║
║  ──────────────────────────────────────────────────────────────────────   ║
║                                                                            ║
║  ┌────────────────────────────────────────────────────────────────────┐  ║
║  │ BOM Material     Declaration File           Mapped    Last Updated  │  ║
║  ├────────────────────────────────────────────────────────────────────┤  ║
║  │ A7658            A7658_PETG.pdf             ✅        Jan 25 14:32  │  ║
║  │ A8362            A8362_Tyvek.pdf            ✅        Jan 25 14:31  │  ║
║  │ B7346            B7346_PE.pdf               ✅        Jan 25 14:30  │  ║
║  │ B7462            ⚠️ Not Mapped              ❌        —             │  ║
║  │ C7236            C7236_PP_Film.pdf          ✅        Jan 25 14:28  │  ║
║  │ C9347            ⚠️ Not Mapped              ❌        —             │  ║
║  └────────────────────────────────────────────────────────────────────┘  ║
║                                                                            ║
║  Upload Progress: 4/6 materials (66.7%)                                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### Key Features

#### Supplier Declarations Table
- **Session-based Checkbox Selection:** ☑️ Select All with indeterminate state
- **Cleaner Actions Column:** Only shows expansion toggle [▼]
- **Row Expansion:** Click [▼] to reveal inline details:
  - Supplier Campaign status (Active/Inactive)
  - Supplier Name (from `ppwr_bom.supplier_name`)
- **Upload Time Display:** Shows when declaration was uploaded (from `supplier_declaration_v1.upload_date`)
- **Missing Indicators:** ❌ for materials without declarations with [📤] upload button
- **Quick Actions Bar:**
  - Select All checkbox
  - Upload Selected button (batch upload for checked rows)
  - Archive button (soft-delete checked declarations)

#### Material → Declaration Mapping Table
- **BOM Material:** From `ppwr_bom.material_id`
- **Declaration File:** From `supplier_declaration_v1.original_filename`
- **Mapped Status:** ✅ if linked via `ppwr_material_declaration_link`, ❌ if not
- **Last Updated:** From `ppwr_material_declaration_link.created_at`

#### Upload Progress Bar
- Shows fraction of materials with declarations
- Visual progress indicator

### Data Source
```sql
-- Supplier Declarations
SELECT 
    sd.id,
    sd.material_id,
    sd.original_filename,
    sd.file_size,
    sd.upload_date,
    pb.supplier_name
FROM supplier_declaration_v1 sd
LEFT JOIN ppwr_bom pb ON sd.material_id = pb.material_id
WHERE pb.sku = 'VET-SYRINGE-001';

-- Material Mapping Status
SELECT 
    pb.material_id,
    sd.original_filename,
    CASE WHEN pmdl.id IS NOT NULL THEN true ELSE false END as is_mapped,
    pmdl.created_at
FROM ppwr_bom pb
LEFT JOIN ppwr_material_declaration_link pmdl ON pb.material_id = pmdl.material_id
LEFT JOIN supplier_declaration_v1 sd ON pmdl.decl_material_v1 = sd.id
WHERE pb.sku = 'VET-SYRINGE-001';
```

---

## 📄 PAGE 3: Evaluation Page (`/ppwr/evaluation?sku=VET-SYRINGE-001`)

### Purpose
Display PPWR assessment results with component-level chemical composition and compliance status.

### UI Layout

```
╔════════════════════════════════════════════════════════════════════════════╗
║  PPWR Evaluation Summary - VET-SYRINGE-001              [← Back] [📥 Export]║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  📊 Assessment Statistics                                                  ║
║  ──────────────────────────────────────────────────────────────────────   ║
║                                                                            ║
║  ┌─────────────┬─────────────┬─────────────┬─────────────────────┐       ║
║  │ Total Files │ Downloaded  │ Conformance │ Non-Conformance     │       ║
║  ├─────────────┼─────────────┼─────────────┼─────────────────────┤       ║
║  │     12      │    8 (67%)  │   6 (75%)   │   2 (25%)          │       ║
║  └─────────────┴─────────────┴─────────────┴─────────────────────┘       ║
║                                                                            ║
║  🧪 Chemical Composition Analysis                                         ║
║  ──────────────────────────────────────────────────────────────────────   ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │ Component  │ Subcomp. │ Material │ Supplier       │ CAS ID      │... │ ║
║  ├──────────────────────────────────────────────────────────────────────┤ ║
║  │ Syringe    │ Barrel   │ A7658    │ PlasticTech    │ 24938-67-8  │... │ ║
║  │ Body       │          │ (PETG)   │ Inc.           │             │    │ ║
║  │────────────────────────────────────────────────────────────────────  │ ║
║  │ Chemical: Polyethylene Terephthalate Glycol (PETG)                  │ ║
║  │ Concentration: 145.50 ppm                                            │ ║
║  │ Status: ✅ Compliant                                                 │ ║
║  ├──────────────────────────────────────────────────────────────────────┤ ║
║  │ Packaging  │ Outer    │ A8362    │ DuPont         │ 25038-59-9  │... │ ║
║  │            │ Wrap     │ (Tyvek)  │ Tyvek Div.     │             │    │ ║
║  │────────────────────────────────────────────────────────────────────  │ ║
║  │ Chemical: High-Density Polyethylene (HDPE)                          │ ║
║  │ Concentration: 89.25 ppm                                             │ ║
║  │ Status: ✅ Compliant                                                 │ ║
║  ├──────────────────────────────────────────────────────────────────────┤ ║
║  │ Plunger    │ Tip      │ B7346    │ RubberSeal     │ 9002-88-4   │... │ ║
║  │            │          │ (PE)     │ Co.            │             │    │ ║
║  │────────────────────────────────────────────────────────────────────  │ ║
║  │ Chemical: Polyethylene (PE)                                          │ ║
║  │ Concentration: 220.75 ppm                                            │ ║
║  │ Status: 🔴 Non-Compliant (Exceeds 200 ppm threshold)                │ ║
║  ├──────────────────────────────────────────────────────────────────────┤ ║
║  │ Box        │ Primary  │ B7462    │ ⚠️ Missing     │ —           │... │ ║
║  │            │          │ (Board)  │ Declaration    │             │    │ ║
║  │────────────────────────────────────────────────────────────────────  │ ║
║  │ Chemical: Unknown                                                    │ ║
║  │ Concentration: —                                                     │ ║
║  │ Status: ⚠️ Awaiting Declaration                                     │ ║
║  ├──────────────────────────────────────────────────────────────────────┤ ║
║  │ Label      │ Adhesive │ C7236    │ AdhesiveTech   │ 9003-07-0   │... │ ║
║  │            │          │ (PP)     │ Solutions      │             │    │ ║
║  │────────────────────────────────────────────────────────────────────  │ ║
║  │ Chemical: Polypropylene Film                                         │ ║
║  │ Concentration: 135.00 ppm                                            │ ║
║  │ Status: ✅ Compliant                                                 │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  [1] [2] [3]                                    Showing 1-5 of 12 materials║
║                                                                            ║
║  Legend:                                                                  ║
║  ✅ Compliant: Meets PPWR requirements                                    ║
║  🔴 Non-Compliant: Exceeds regulatory thresholds                         ║
║  ⚠️ Awaiting Declaration: No supplier data received                      ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### Key Features

#### Statistics Cards
- **Total Files:** Count of distinct materials in BOM (`ppwr_bom`)
- **Downloaded:** Count of materials with chemical data (`ppwr_result`)
- **Conformance:** Count of materials with status containing "compliant"
- **Non-Conformance:** Count of materials with status containing "non-compliant"

#### Chemical Composition Table
- **Component/Subcomponent:** From `ppwr_bom.component_description` and `subcomponent_description`
- **Material:** From `ppwr_bom.material_id` and `material_name`
- **Supplier:** From `ppwr_result.supplier_name`
- **CAS ID:** From `ppwr_result.cas_id`
- **Chemical:** From `ppwr_result.chemical`
- **Concentration:** From `ppwr_result.concentration` (formatted as "145.50 ppm")
- **Status:** From `ppwr_result.status` with color coding:
  - ✅ Green for "Compliant"
  - 🔴 Red for "Non-Compliant"
  - ⚠️ Yellow for "Unknown" or missing data

#### SKU Filtering
- URL parameter: `/ppwr/evaluation?sku=VET-SYRINGE-001`
- Filter applied in SQL query before rendering
- Shows only materials for specified SKU

#### Export Function
- [📥 Export] button generates Excel file with all evaluation data
- Includes all columns with color-coded status cells
- Filename format: `PPWR_Evaluation_{SKU}_{timestamp}.xlsx`

### Data Source
```sql
SELECT 
    pb.component,
    pb.component_description,
    pb.subcomponent,
    pb.subcomponent_description,
    pb.material_id,
    pb.material_name,
    pr.supplier_name,
    pr.cas_id,
    pr.chemical,
    pr.concentration,
    pr.status
FROM ppwr_bom pb
LEFT JOIN ppwr_result pr ON pb.material_id = pr.material_id
WHERE pb.sku = 'VET-SYRINGE-001'
ORDER BY pb.component, pb.subcomponent, pb.material_id;
```

---

## 🎨 Design Notes

### Color Scheme
- **Primary Blue:** `#0d6efd` - Action buttons, links
- **Success Green:** `#198754` - Compliant status, checkmarks
- **Danger Red:** `#dc3545` - Non-compliant status, errors
- **Warning Yellow:** `#ffc107` - Missing data, in-progress
- **Light Gray:** `#f8f9fa` - Table backgrounds, secondary elements

### Responsive Behavior
- **Desktop (>1200px):** Full layout as shown in mockups
- **Tablet (768px-1200px):** Stacked cards, simplified tables
- **Mobile (<768px):** Single column layout, touch-optimized buttons

### Accessibility
- **ARIA Labels:** All interactive elements labeled
- **Keyboard Navigation:** Full tab/enter support
- **Screen Reader:** Table headers properly associated
- **Color Contrast:** WCAG AA compliant (4.5:1 minimum)

### Loading States
- **Skeleton Screens:** For initial page loads
- **Spinners:** For AJAX operations (declaration upload)
- **Progress Bars:** For batch operations (multi-file upload)
- **Toast Notifications:** For success/error messages

---

## 🔗 Navigation Flow

```
┌──────────────┐
│  Dashboard   │
│      /       │
└──────┬───────┘
       │
       ↓ [Start Button]
┌──────────────────────────────┐
│   PPWR Assessment Tab        │
│   /assessment/<sku>?tab=ppwr │
└──────┬───────────────────────┘
       │
       ↓ [View Evaluation]
┌────────────────────────────┐
│   Evaluation Page          │
│   /ppwr/evaluation?sku=... │
└────────────────────────────┘
```

### URL Parameters
- Dashboard: No params required
- Assessment: `<sku>` in path, `?tab=ppwr` in query
- Evaluation: `?sku=<value>` in query (optional, shows all if omitted)

---

## 📱 User Workflows

### Workflow 1: New Product Upload
1. **Dashboard:** Click [➕ Upload BOM]
2. **Upload Modal:** Select Excel file, choose route (PFAS/PPWR)
3. **Dashboard:** Product appears with timestamp and "Missing Files" status
4. **Assessment Tab:** Click [▶ Start] to manage declarations

### Workflow 2: Upload Supplier Declarations
1. **Assessment Tab:** Click [📤] next to missing material
2. **Upload Modal:** Select PDF file
3. **Assessment Tab:** Declaration appears with upload timestamp
4. **Automatic Mapping:** System links declaration to material via `material_id`

### Workflow 3: View Evaluation
1. **Assessment Tab:** Click [🔍 View Evaluation]
2. **Evaluation Page:** Review component-level chemical data
3. **Evaluation Page:** Check compliance status for each material
4. **Evaluation Page:** Click [📥 Export] to download Excel report

### Workflow 4: Bulk Operations
1. **Assessment Tab:** Check multiple materials
2. **Assessment Tab:** Click [☑️ Select All] to select all visible
3. **Quick Actions:** Click [📤 Upload Selected] or [🗑️ Archive]
4. **Batch Processing:** System processes all checked items

---

## 🐛 Error Handling

### Missing Data Indicators
- **❌ Missing Declaration:** Red X icon with [📤] upload button
- **⚠️ Not Mapped:** Yellow warning with auto-map suggestion
- **🔴 Non-Compliant:** Red status badge with threshold details
- **—** (em dash): Used for null/empty fields

### Error Messages
- **Upload Failed:** "Failed to upload declaration for material {id}. Please check file format."
- **Mapping Failed:** "Could not map declaration to material. BOM entry may be missing."
- **Query Failed:** "Failed to load evaluation data. Please contact administrator."

### Fallback Behavior
- **Empty Dashboard:** Show "No products uploaded yet" message with [➕ Upload BOM] CTA
- **Empty Assessment:** Show "No materials found for this SKU" with back button
- **Empty Evaluation:** Show "No chemical data available. Upload declarations to continue."

---

## ✨ Implemented Features

- ✅ Dashboard with upload timestamps (`ppwr_bom.uploaded_at`)
- ✅ PPWR tab with session-based checkbox selection
- ✅ Cleaner Actions column (expansion toggle only)
- ✅ Row expansion showing supplier campaign and name
- ✅ Evaluation page querying `ppwr_result` + `ppwr_bom`
- ✅ SKU filtering in evaluation page
- ✅ Component/subcomponent columns displayed
- ✅ Upload time display for declarations
- ✅ Mapping status indicators
- ✅ Compliance status color coding

---

## 📝 Technical Notes

### Frontend Framework
- **Flask 3.x** with Jinja2 templates
- **Bootstrap 5.3** for responsive layout
- **jQuery 3.x** for AJAX and DOM manipulation
- **DataTables** for sortable/filterable tables

### Backend API
- **FastAPI 0.109** for backend services
- **PostgreSQL 13+** for data storage
- **SQLAlchemy 2.x** for ORM

### File Storage
- **Supplier Declarations:** Stored as `BYTEA` in `supplier_declaration_v1.file_data`
- **Maximum File Size:** 10 MB per PDF
- **Allowed Formats:** PDF, DOCX, XLSX

### Performance
- **Pagination:** 10 items per page default
- **Lazy Loading:** Declaration file bytes loaded on-demand
- **Caching:** Material counts cached for 5 minutes
- **Indexing:** All foreign keys indexed for fast JOINs

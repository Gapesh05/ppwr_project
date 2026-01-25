# PPWR Tab - Updated UI Visual Guide

## Table Structure (After Implementation)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ PPWR Assessment - SKU: 12345                                                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                   │
│  Quick Actions:                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │ ☐ Select All (0)      [Download Selected] [Delete Selected] [Evaluate Selected]        │    │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │ ☐ │ Material      │ Supplier      │ Declaration                │ Uploaded At  │ Actions │    │
│  ├───┼───────────────┼───────────────┼────────────────────────────┼──────────────┼─────────┤    │
│  │ ☑ │ A7658         │ Acme Corp     │ 📄 A7658_PETG.pdf         │ Jan 15, 2:30 │[Details▼]│   │
│  │   │ PETG          │               │    150.2 KB                │  PM          │         │    │
│  │   │               │               │    🕐 Jan 15, 2:30 PM      │              │         │    │
│  ├───┴───────────────┴───────────────┴────────────────────────────┴──────────────┴─────────┤    │
│  │   ┌─────────────────────────────────────────────────────────────────────────────────┐   │    │
│  │   │ ℹ️ Material Details: A7658                                                      │   │    │
│  │   │                                                                                   │   │    │
│  │   │ Supplier Campaign: [Active]        Supplier Name: Acme Corp                     │   │    │
│  │   └─────────────────────────────────────────────────────────────────────────────────┘   │    │
│  ├───┬───────────────┬───────────────┬────────────────────────────┬──────────────┬─────────┤    │
│  │ ☑ │ A8362         │ Vendor XYZ    │ 📄 A8362_Tyvek.pdf        │ Jan 14, 9:15 │[Details▼]│   │
│  │   │ 1073B Tyvek   │               │    89.5 KB                 │  AM          │         │    │
│  │   │               │               │    🕐 Jan 14, 9:15 AM      │              │         │    │
│  ├───┼───────────────┼───────────────┼────────────────────────────┼──────────────┼─────────┤    │
│  │ ☐ │ B7346         │ Supplier Co   │ ⚠️ Not uploaded            │ —            │[Upload] │    │
│  │   │ PE            │               │                            │              │         │    │
│  └───┴───────────────┴───────────────┴────────────────────────────┴──────────────┴─────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Changes

### 1. Declaration Column (Column 4)
**BEFORE:**
```
┌─────────────────────────┐
│ [✓ A7658_PETG.pdf    ] │  ← Button showing filename
└─────────────────────────┘
```

**AFTER:**
```
┌─────────────────────────────┐
│ 📄 A7658_PETG.pdf          │  ← Clickable PDF link (blue)
│    150.2 KB                 │  ← File size
│    🕐 Jan 15, 2:30 PM       │  ← Upload timestamp
└─────────────────────────────┘

OR (if not uploaded):

┌─────────────────────────────┐
│ ⚠️ Not uploaded             │  ← Warning message
└─────────────────────────────┘
```

### 2. Actions Column (Column 5)
**BEFORE (Mixed Purpose):**
```
┌──────────────┐
│ [▼]          │  ← Toggle button (icon only)
└──────────────┘
```

**AFTER (Expansion Toggle Only):**
```
WITH DECLARATION:
┌──────────────┐
│ [Details ▼]  │  ← Expansion toggle button (text + icon)
└──────────────┘

WITHOUT DECLARATION:
┌──────────────┐
│ [Upload]     │  ← Upload button (primary blue)
└──────────────┘
```

### 3. Expansion Row Content
**BEFORE (Redundant Info):**
```
┌─────────────────────────────────────────────────────────────┐
│ Material Details: A7658                                     │
│                                                              │
│ Material Name: PETG                      ← Already visible  │
│ Declaration Status: Uploaded             ← Already visible  │
│ Supplier Campaign: Active                                   │
│ Supplier Name: Acme Corp                                    │
└─────────────────────────────────────────────────────────────┘
```

**AFTER (Clean & Focused):**
```
┌─────────────────────────────────────────────────────────────┐
│ ℹ️ Material Details: A7658                                  │
│                                                              │
│ Supplier Campaign: [Active]       Supplier Name: Acme Corp  │
│                   (green badge)                              │
└─────────────────────────────────────────────────────────────┘
```

## Delete/Download Operations

**BEFORE:**
- Individual delete buttons in each row ❌
- Individual download buttons in each row ❌
- Bulk action buttons at top ✓

**AFTER:**
- No individual action buttons ✓
- All operations via bulk action buttons only ✓
- Cleaner, less cluttered table ✓

## User Interaction Flow

### Opening Expansion
1. User clicks **[Details ▼]** button
2. Expansion row slides in below with light gray background
3. Icon changes to **[Details ▲]**
4. Shows supplier campaign badge and supplier name

### Closing Expansion
1. User clicks **[Details ▲]** button again
2. Expansion row slides out
3. Icon changes back to **[Details ▼]**

### Multiple Expansions
- Users can open multiple expansion rows simultaneously
- Each row toggles independently
- No limit on concurrent expansions

### Upload Flow
1. Materials without declarations show **[Upload]** button
2. Click to upload → file dialog opens
3. After upload → button changes to **[Details ▼]**
4. Declaration column updates with PDF link

## Visual States

### Expansion Row Card
```css
Background: Light gray (#f8f9fa)
Card: White with subtle shadow
Border: None (clean modern look)
Padding: 3rem (generous spacing)
```

### Supplier Campaign Badge
```css
Active: Green background (bg-success)
Not Assigned: Yellow background (bg-warning text-dark)
Font: Bold, uppercase
```

### PDF Link
```css
Icon: Red PDF icon (bi-file-earmark-pdf text-danger)
Text: Blue underlined on hover
Target: Opens in new tab (_blank)
```

### Chevron Icons
```css
Closed State: bi-chevron-down
Open State: bi-chevron-up
Color: Primary blue
Smooth transition on toggle
```

## Benefits Summary

1. **Cleaner UI**
   - Single-purpose Actions column
   - Reduced visual clutter
   - Professional appearance

2. **Better UX**
   - Clickable PDF links (intuitive)
   - Clear expansion toggle with visual feedback
   - Consistent bulk operations

3. **Improved Information Architecture**
   - No redundant data in expansion
   - Focus on key supplier information
   - Clear visual hierarchy

4. **Efficient Workflows**
   - Multi-row operations in action bar
   - No need for individual action buttons
   - Select All + Bulk Actions = Fast processing

## Responsive Behavior

### Desktop (>768px)
- Full 6-column layout
- Expansion row spans all columns
- Side-by-side supplier info

### Mobile (<768px)
- Responsive column widths
- Expansion card stacks vertically
- Touch-friendly button sizes

## Accessibility Features

- ✓ ARIA labels on checkboxes
- ✓ Clear button titles
- ✓ Keyboard navigation support
- ✓ Screen reader friendly
- ✓ High contrast badges
- ✓ Focus indicators

## Color Coding

```
PDF Icon:        🔴 Red (#dc3545)
Success Badge:   🟢 Green (#198754)
Warning Badge:   🟡 Yellow (#ffc107)
Primary Button:  🔵 Blue (#0d6efd)
Info Icon:       🔵 Blue (#0dcaf0)
Text Muted:      ⚫ Gray (#6c757d)
```

## Icon Reference

```
📄  bi-file-earmark-pdf    (PDF files)
⚠️  bi-exclamation-circle  (Not uploaded)
🕐  bi-clock               (Upload timestamp)
▼   bi-chevron-down        (Expand)
▲   bi-chevron-up          (Collapse)
ℹ️  bi-info-circle         (Details card)
📤  bi-upload              (Upload button)
```

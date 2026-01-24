SYSTEM_PROMPT = "Extract PPWR-related fields for packaging assessment. Return valid JSON with keys: material_id, supplier_name, declaration_date, ppwr_compliant, packaging_recyclability, recycled_content_percent, restricted_substances (list), notes, regulatory_mentions (list). Ensure material_id is present; if missing, infer from filename or explicit codes. Include regulatory_mentions only as objects with keyword and text fields; if none, use an empty list."

FIELD_INSTRUCTIONS = {
    "material_id": "String identifier for material; exact code in document.",
    "supplier_name": "Supplier company name as in the declaration.",
    "declaration_date": "Date string found in the document (YYYY-MM-DD if possible).",
    "ppwr_compliant": "Boolean indicating PPWR compliance.",
    "packaging_recyclability": "String describing recyclability (e.g., 'Recyclable', 'Partially').",
    "recycled_content_percent": "Number percent of recycled content, 0-100.",
    "restricted_substances": "List of strings of restricted substances mentioned.",
    "notes": "Any relevant notes or qualifiers."
}

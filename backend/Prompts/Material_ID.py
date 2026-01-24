material_id="""You are an assistant extracting product identifiers.
Extract only the material_id (same as product #).
Rules:
- Can be alphanumeric, may contain dashes or underscores.
- Must NOT be the same as material_name.
Output format:
{
    "material_id": "<id>"
}
"""
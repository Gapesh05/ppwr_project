supplier_name="""Extract supplier information from user-provided text related to the following field: supplier_name (same as vendor name) 

Rules: 
Matching Criteria: 
supplier_name is the company providing/manufacturing the product or service. Look for company names in letterhead, signature blocks, document headers, or companies mentioned as the document sender/author.

Field Relationships: 
supplier_name is the same as vendor name.

Missing Company Case: 
If no clear company name is found, return supplier_name as "Not specified".

- Treat any capitalized word sequences that could be a company name as a valid supplier_name.
- Include the full official name, even if it contains generic words like "Life Long".
- If a company is providing/manufacturing the product or service in context, extract it as supplier_name.


Output Format: 
Return one dictionary following this format: 
{     
    "supplier_name": "Westlake" or "Nordson" or "Memory Products" 
}
"""
# queries.py
from backend.Prompts.Cas_Number import cas_number
from backend.Prompts.Chemical_Name import chemical_name
from backend.Prompts.Concentration_PPM import quantity
from backend.Prompts.Material_ID import material_id
from backend.Prompts.Material_Name import material_name
from backend.Prompts.Supplier_Name import supplier_name
from backend.Prompts.PPWR_Material_ID import SYSTEM_PROMPT as PPWR_SYSTEM_PROMPT
from backend.Prompts.PPWR_Compliance_Flags import SYSTEM_PROMPT as PPWR_FLAGS_PROMPT
from backend.Prompts.PPWR_Notes import SYSTEM_PROMPT as PPWR_NOTES_PROMPT
from backend.Prompts.PPWR_Regulatory_Mentions import SYSTEM_PROMPT as PPWR_MENTIONS_PROMPT

queries = {
    "material_id": {
        "query": "Extract the material_id (same as product # or part number) from the document.",
        "prompt": material_id
    },
    "material_name": {
        "query": "Extract the material name (PFAS name) from the document.",
        "prompt": material_name
    },
    "supplier_name": {
        "query": "Extract the supplier (vendor) name from the document.",
        "prompt": supplier_name
    },
    "cas_number": {
        "query": "Extract the CAS number from the document.",
        "prompt": cas_number
    },
    "chemical_name": {
        "query": "Extract the PFAS chemical substance name from the document.",
        "prompt": chemical_name
    },
    "quantity": {
        "query": "Extract the concentration/quantity (in ppm) from the document.",
        "prompt": quantity
    }
}

# Minimal PPWR queries/prompts bundle (LLM will receive combined instructions)
ppwr_queries = {
    "system": PPWR_SYSTEM_PROMPT,
    "flags": PPWR_FLAGS_PROMPT,
    "notes": PPWR_NOTES_PROMPT,
    "mentions": PPWR_MENTIONS_PROMPT,
}

import logging
import traceback
import sys
import re
from backend.config import get_config_loader, CONFIG
from backend.models import AzureEmbedder, AzureLLM
from backend.retriever import connect_chromadb, get_collection, retrieve_documents, extract_components, raw_prompt_template, extract_text_from_pdf_bytes
from backend.parse_llm import parse_llm_response, parse_ppwr_output
from backend.queries import ppwr_queries
from backend.models import SessionLocal, PPWRAssessment
import json
# -------------------------
# CONFIGURATION HELPER FUNCTIONS
# -------------------------
def build_runtime_config(embedder_instance, llm_instance):
    """Build runtime configuration with model instances"""
    config_loader = get_config_loader()

    return {
        "embedder": embedder_instance,
        "llm": llm_instance,
        "chroma_host": config_loader.get("storage", "chroma", "host"),
        "chroma_port": config_loader.get("storage", "chroma", "port"),
        "max_results": config_loader.get("generation", "max_results", default=5),
        "temperature": config_loader.get("generation", "temperature", default=0.4),
        "max_tokens": config_loader.get("generation", "max_tokens", default=2048)
    }

def get_collection_name():
    """Get default collection name from config"""
    config_loader = get_config_loader()
    collection_name = config_loader.get("storage", "chroma", "collection_name", default="dhf_chunks")

    if not isinstance(collection_name, str):
        logging.error(f"Collection name is not a string: {collection_name} (type: {type(collection_name)})")
        return "dhf_chunks"

    logging.info(f"Using collection name: {collection_name}")
    return collection_name

def initialize_azure_models():
    """Initialize Azure OpenAI embedder and LLM"""
    config_loader = get_config_loader()

    embedder_config = config_loader.get("embeddings", "azure")
    embedder = AzureEmbedder(embedder_config)

    llm_config = config_loader.get("llms", "azure")
    llm = AzureLLM(llm_config)

    return embedder, llm

# -------------------------
# MAIN RETRIEVAL FUNCTIONS
# -------------------------
def retrieve_content_prompt(config, collection_name, query_text, role, prompt_data, full_document_search, where_filter, where_document):
    """Retrieve content and generate prompt with LLM response"""
    if not isinstance(collection_name, str):
        logging.error(f"collection_name must be string, got {type(collection_name)}: {collection_name}")
        return "Error: Invalid collection name provided."

    if not isinstance(query_text, str):
        logging.error(f"query_text must be string, got {type(query_text)}: {query_text}")
        return "Error: Invalid query text provided."

    try:
        embedder = config["embedder"]
        llm = config["llm"]
        chroma_host = config["chroma_host"]
        chroma_port = config["chroma_port"]
        max_results = config.get("max_results", 5)
        temperature = config["temperature"]
        max_tokens = config["max_tokens"]

        client = connect_chromadb(chroma_host, chroma_port)
        collection = get_collection(client, collection_name)

        extracted = extract_components(query_text)
        question = extracted.get("question")
        field = extracted.get("field")
        target_doc_id = extracted.get("document_id")
        filter_values = extracted.get("section")

        if not isinstance(filter_values, list) and filter_values:
            filter_values = [filter_values]

        question_text = f"{question}." if question else query_text
        embedding = embedder.embed(question_text)

        meta_filter = {}
        if field:
            meta_filter["section"] = {"$contains": field}
        if target_doc_id:
            meta_filter["source"] = {"$contains": target_doc_id}

        results = retrieve_documents(collection, embedding, filter_values, where_filter, where_document, max_results, full_document_search)
        documents = results.get("documents", [[]])

        if documents and isinstance(documents[0], list):
            documents = documents[0]

        context = "\n\n".join(str(doc).strip() for doc in documents if str(doc).strip())

        if not context:
            context = "No relevant documents found in the knowledge base for this query."

        prompt = raw_prompt_template(context, prompt_data, role)

        return llm.generate(prompt, context, question_text, temperature, max_tokens)

    except Exception as e:
        logging.error(f"Error in retrieve_content_prompt: {e}")
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return f"Error processing query: {str(e)}"

def retrieve_content_from_documents(config, collection_name, query_text, full_document_search, where_filter, where_document):
    """Retrieve content from documents without LLM generation"""
    if not isinstance(collection_name, str):
        logging.error(f"collection_name must be string, got {type(collection_name)}: {collection_name}")
        return {"documents": [[]], "metadatas": [[]]}

    if not isinstance(query_text, str):
        logging.error(f"query_text must be string, got {type(query_text)}: {query_text}")
        return {"documents": [[]], "metadatas": [[]]}

    try:
        embedder = config["embedder"]
        chroma_host = config["chroma_host"]
        chroma_port = config["chroma_port"]
        max_results = config.get("max_results", 5)

        client = connect_chromadb(chroma_host, chroma_port)
        collection = get_collection(client, collection_name)

        extracted = extract_components(query_text)
        question = extracted.get("question")
        field = extracted.get("field")
        target_doc_id = extracted.get("document_id")
        filter_values = extracted.get("section")

        if not isinstance(filter_values, list) and filter_values:
            filter_values = [filter_values]

        question_text = f"{question}." if question else query_text
        embedding = embedder.embed(question_text)

        meta_filter = {}
        if field:
            meta_filter["section"] = {"$contains": field}
        if target_doc_id:
            meta_filter["source"] = {"$contains": target_doc_id}

        results = retrieve_documents(collection, embedding, filter_values, where_filter, where_document, max_results, full_document_search)

        return results

    except Exception as e:
        logging.error(f"Error in retrieve_content_from_documents: {e}")
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return {"documents": [[]], "metadatas": [[]]}

# -------------------------
# MAIN EXECUTION (REAL-TIME USAGE EXAMPLE)
# -------------------------
if __name__ == "__main__":
    logging.info("=== Starting Real-Time RAG Pipeline ===")

    try:
        # Initialize Azure models
        embedder, llm = initialize_azure_models()
        runtime_config = build_runtime_config(embedder, llm)
        collection_name = get_collection_name()

        # Example real-time query — replace with dynamic input in production
        query = "Extract material id, material name, supplier name, cas number, concentration, chemical name from the PFAS document."

        logging.info(f"Processing query: {query}")

        # Define role and prompt instruction
        role = "You are a precise data extraction assistant."
        prompt_data = """Identify and extract tabular data related to material_id, material_name, cas_number, chemical_name, quantity, supplier_name from text given by user. get all relevant data

Chemical name is PFAS substance name. Part number and material id (could be alphanumeric with dashes or underscores) are the same. Material name is not the same as part number or material id, and vice versa. Supplier name is the same as vendor name. Material Id is 005 or Material name is octofluro get relevant data only thos. if exactly anymatches with one of both else return []

Give in the form of a dictionary or multiple dictionaries which could be used to create a pandas dataframe. Return "" for any information missing.

For cases where PFAS is absent in that material, you will only be able to capture material_id and supplier_name; leave the rest as blank strings.

Provide just the dictionary or dictionaries (separated by comma if multiple), and nothing else (no JSON keyword, no explanation, no formatting).

Example format:

{
    "material_id": "234741",
    "material_name": "silicone",
    "cas_number": "19430-93-4",
    "chemical_name": "1-Hexene,3,3,4,4,5,5,6,6,6-nonafluoro-",
    "quantity": "150 ppm",
    "supplier_name": "Memory Products"
}
"""

        # Generate AI response
        response = retrieve_content_prompt(
            runtime_config,
            collection_name,
            query,
            role,
            prompt_data,
            full_document_search="No",
            where_filter="",
            where_document=""
        )

        print("\n=== AI RESPONSE ===")
        print(response)

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


# -------------------------
# PPWR Pipeline
# -------------------------
MENTION_PATTERNS = {
    "PPWD 94/62/EC": r"94/62\s*/?\s*ec|packaging and packaging waste directive|packaging directive|ppwd",
    "PPWD 94/62/1": r"94/62/1",
    "PPWR (EU) 2025/40": r"2025/40|packaging and packaging waste regulation|ppwr",
    "Lead (Pb)": r"\blead(?!\s+to)\b|\bpb\b",
    "Cadmium (Cd)": r"\bcadmium\b|\bcd\b",
    "Hexavalent Chromium (Cr6+)": r"hexavalent chromium|cr6|cr\(vi\)",
}


def extract_regulatory_mentions_windows(text: str, line_window: int = 50) -> list[dict]:
    """Deterministically capture keyword windows using ±line_window lines around the first match in each line block."""
    if not text:
        return []

    lines = text.splitlines()
    mentions = []
    seen = set()

    for keyword, pattern in MENTION_PATTERNS.items():
        for idx, line in enumerate(lines):
            if keyword == "Lead (Pb)" and re.search(r"lead\s+to", line, flags=re.IGNORECASE):
                continue
            if re.search(pattern, line, flags=re.IGNORECASE):
                start_idx = max(0, idx - line_window)
                end_idx = min(len(lines), idx + line_window + 1)
                window_text = "\n".join(l for l in lines[start_idx:end_idx])
                cleaned = window_text.strip()
                if cleaned:
                    key = (keyword, cleaned)
                    if key not in seen:
                        mentions.append({"keyword": keyword, "text": cleaned})
                        seen.add(key)
                break  # Only take first hit per keyword to avoid duplicates

    return mentions


def summarize_mentions_with_llm(llm, snippets: list[dict]) -> list[dict]:
    """Ask LLM to set compliant flag on provided line-window snippets; returns [{keyword,text,compliant}]."""
    if not snippets:
        return []
    try:
        prompt_items = []
        for s in snippets:
            kw = s.get('keyword', '')
            tx = s.get('text', '')
            prompt_items.append({"keyword": kw, "text_window": tx})

        prompt = (
            "You are checking packaging regulatory compliance. For each item, decide if the text explicitly states compliance, "
            "no intentional addition, or below limits for the cited keyword. compliant=true if it affirms compliance/absence/below limits; "
            "compliant=false if it states non-compliance or exceedance; compliant=null if unclear. Always return the quoted evidence used. "
            "Return JSON list only.\n\nItems:" + json.dumps(prompt_items)
        )
        resp = llm.generate(prompt, "", "Assess compliance", temperature=0, max_tokens=700)
        parsed = parse_llm_response(resp)
        cleaned = []
        for p in parsed:
            if not isinstance(p, dict):
                continue
            kw = str(p.get('keyword') or '').strip()
            ev = str(p.get('evidence') or p.get('text') or '').strip()
            comp = p.get('compliant')
            if isinstance(comp, str):
                c = comp.strip().lower()
                comp = True if c in {'true','yes','y','1'} else False if c in {'false','no','n','0'} else None
            elif comp not in (True, False):
                comp = None
            if kw or ev:
                entry = {'keyword': kw, 'text': ev}
                entry['compliant'] = comp
                cleaned.append(entry)
        return cleaned
    except Exception as e:
        logging.warning(f"LLM mention summarization failed: {e}")
        return []


def run_ppwr_pipeline(bom_material_ids: list[str], pdfs: list[dict]) -> dict:
    """Process supplier declaration PDFs and join to BOM rows by material_id.

    pdfs: list of { 'filename': str, 'bytes': bytes }
    Returns dict with 'inserted', 'updated', 'skipped'.
    """
    try:
        embedder, llm = initialize_azure_models()
        runtime_config = build_runtime_config(embedder, llm)
        role = "You are a precise PPWR data extraction assistant."
        system_prompt = ppwr_queries.get('system', '')
        flags_prompt = ppwr_queries.get('flags', '')
        notes_prompt = ppwr_queries.get('notes', '')
        mentions_prompt = ppwr_queries.get('mentions', '')

        inserted = updated = skipped = 0
        skipped_reasons = []
        session = SessionLocal()

        # Prepare fast lookup of BOM material ids
        bom_set = set([str(m).strip() for m in bom_material_ids if str(m).strip()])
        bom_set_upper = {m.upper() for m in bom_set}

        for pdf in pdfs:
            fname = pdf.get('filename') or 'document.pdf'
            file_bytes = pdf.get('bytes') or b''
            context = extract_text_from_pdf_bytes(file_bytes)
            if not context:
                skipped += 1
                skipped_reasons.append({"file": fname, "reason": "empty_text"})
                continue

            # Combine prompts into one simple JSON-directed query
            prompt = f"{system_prompt}\n\n{flags_prompt}\n\n{notes_prompt}\n\n{mentions_prompt}\n\nReturn only JSON."
            full_prompt = raw_prompt_template(context, prompt, role)
            llm_resp = llm.generate(full_prompt, context, "Extract PPWR fields", temperature=0.2, max_tokens=1024)
            items = parse_llm_response(llm_resp)
            normalized = parse_ppwr_output(items)
            fallback_mentions = extract_regulatory_mentions_windows(context, line_window=50)
            llm_mentions = summarize_mentions_with_llm(llm, fallback_mentions)
            if not normalized and len(bom_set) == 1:
                # Ensure we still persist mention evidence even if the LLM extraction is empty
                normalized = [{
                    'material_id': list(bom_set)[0],
                    'supplier_name': None,
                    'declaration_date': None,
                    'ppwr_compliant': None,
                    'packaging_recyclability': None,
                    'recycled_content_percent': None,
                    'restricted_substances': [],
                    'notes': None,
                    'regulatory_mentions': llm_mentions if llm_mentions else fallback_mentions,
                }]
            seen_materials = set()

            for rec in normalized:
                mid_raw = rec.get('material_id') or ''
                mid_norm = str(mid_raw).strip()
                mid_upper = mid_norm.upper()

                # Fallback: if LLM did not return material_id, and we have exactly one BOM id, use it.
                if not mid_norm and len(bom_set) == 1:
                    mid_norm = list(bom_set)[0]
                    mid_upper = mid_norm.upper()
                # Allow case-insensitive match to BOM
                if mid_upper in bom_set_upper:
                    # Resolve to original casing from bom_set if possible
                    for m in bom_set:
                        if m.upper() == mid_upper:
                            mid_norm = m
                            break
                else:
                    # If only one BOM id was provided, fall back to it to avoid losing the assessment
                    if len(bom_set) == 1:
                        mid_norm = list(bom_set)[0]
                        mid_upper = mid_norm.upper()
                    else:
                        skipped += 1
                        skipped_reasons.append({"file": fname, "reason": "material_not_in_bom", "material_id": mid_norm})
                        continue

                # Avoid multiple inserts for the same material within one PDF
                if mid_upper in seen_materials:
                    skipped += 1
                    skipped_reasons.append({"file": fname, "reason": "duplicate_material_in_pdf", "material_id": mid_norm})
                    continue
                seen_materials.add(mid_upper)

                # Derive compliance: if restricted_substances present and non-empty -> non-compliant, else compliant
                restricted_list = rec.get('restricted_substances', []) or []
                ppwr_compliant = rec.get('ppwr_compliant')
                if ppwr_compliant is None:
                    ppwr_compliant = False if len(restricted_list) > 0 else True

                # Upsert into PPWRAssessment
                existing = session.query(PPWRAssessment).filter_by(material_id=mid_norm).first()
                reg_mentions = rec.get('regulatory_mentions') or []
                # Prefer LLM-assessed mentions; fall back to regex snippets if LLM empty
                mentions_source = llm_mentions if llm_mentions else fallback_mentions
                if mentions_source:
                    merged = []
                    seen_mentions = set()
                    for m in reg_mentions + mentions_source:
                        if not isinstance(m, dict):
                            continue
                        keyword = str(m.get('keyword') or '').strip()
                        text_val = str(m.get('text') or '').strip()
                        compliant_val = m.get('compliant')
                        if isinstance(compliant_val, str):
                            c = compliant_val.strip().lower()
                            compliant_val = True if c in {'true','yes','y','1'} else False if c in {'false','no','n','0'} else None
                        elif compliant_val not in (True, False):
                            compliant_val = None
                        if not keyword and not text_val:
                            continue
                        key = (keyword.lower(), text_val)
                        if key in seen_mentions:
                            continue
                        seen_mentions.add(key)
                        entry = {'keyword': keyword, 'text': text_val}
                        if compliant_val in (True, False, None):
                            entry['compliant'] = compliant_val
                        merged.append(entry)
                    reg_mentions = merged

                payload = {
                    'material_id': mid_norm,
                    'supplier_name': rec.get('supplier_name'),
                    'declaration_date': rec.get('declaration_date'),
                    'ppwr_compliant': ppwr_compliant,
                    'packaging_recyclability': rec.get('packaging_recyclability'),
                    'recycled_content_percent': rec.get('recycled_content_percent'),
                    'restricted_substances_json': json.dumps(restricted_list),
                    'notes': rec.get('notes'),
                    'source_path': fname,
                    'regulatory_mentions_json': json.dumps(reg_mentions),
                }
                if existing:
                    for k, v in payload.items():
                        setattr(existing, k, v)
                    updated += 1
                else:
                    session.add(PPWRAssessment(**payload))
                    inserted += 1
            session.commit()

        return {'inserted': inserted, 'updated': updated, 'skipped': skipped, 'skipped_reasons': skipped_reasons}
    except Exception as e:
        logging.error(f"PPWR pipeline failed: {e}")
        return {'error': str(e)}
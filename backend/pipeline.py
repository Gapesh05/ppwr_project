import logging
import traceback
import sys
import re
from backend.config import get_config_loader, CONFIG
from backend.models import AzureEmbedder, AzureLLM
from backend.retriever import connect_chromadb, get_collection, retrieve_documents, extract_components, raw_prompt_template, extract_text_from_pdf_bytes
from backend.parse_llm import parse_llm_response, parse_ppwr_output
from backend.queries import ppwr_queries
from backend.models import SessionLocal
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

        logging.info(f"AI RESPONSE: {response}")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


# -------------------------
# PPWR Pipeline
# -------------------------
MENTION_PATTERNS = {
    "PPWD 94/62/EC": r"(?i)94/62\s*/?\s*ec|packaging and packaging waste directive|packaging directive(?!\s+for)|ppwd",
    "PPWD 94/62/1": r"(?i)94/62/1",
    "PPWR (EU) 2025/40": r"(?i)2025/40|packaging and packaging waste regulation|ppwr",
    # Exclude "lead to", "mislead", and "lead time" - only match metal references
    "Lead (Pb)": r"(?i)\blead(?!\s+(to|time|in|by|through))\b(?![a-z])|\bpb\b(?!\s*-?\s*(rom|&j|ratio))",
    # Exclude "CD", "CD-ROM", require context like "metal", "ppm", or chemical notation
    "Cadmium (Cd)": r"(?i)\bcadmium\b|\bcd\b(?=\s*(metal|ppm|\(|concentration|content|level))",
    "Hexavalent Chromium (Cr6+)": r"(?i)hexavalent chromium|cr\s*6\+?|cr\s*\(vi\)|chrome\s*6",
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


# OLD DIRECT EXTRACTION PIPELINE REMOVED - Now using RAG-based approach with ChromaDB
# The new workflow:
# 1. Upload PDF -> /ppwr/index-declaration (chunks + embeds to ChromaDB)
# 2. Evaluate -> /ppwr/assess (queries ChromaDB, retrieves relevant chunks, feeds to LLM)
# See backend/main.py for new RAG-based endpoints
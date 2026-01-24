import chromadb
import json
import re
import logging
from typing import List, Dict, Any, Optional
from chromadb.config import Settings
import io
try:
    import PyPDF2
except Exception:
    PyPDF2 = None

# -------------------------
# CHROMA RETRIEVER FUNCTIONS
# -------------------------
def connect_chromadb(host, port):
    """Connect to ChromaDB instance"""
    try:
        return chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(anonymized_telemetry=False)
        )
    except Exception as e:
        logging.error(f"Failed to connect to ChromaDB at {host}:{port} - {e}")
        raise e

def get_collection(client, name):
    """Get collection from ChromaDB client"""
    try:
        return client.get_collection(name=name)
    except Exception as e:
        logging.error(f"Failed to get collection '{name}': {e}")
        raise e

def retrieve_documents(collection, embedding, filter_values, where_filter, where_document, max_results, full_document_search):
    """Retrieve documents from ChromaDB collection"""
    results = None
    where = None

    # Handle where_document
    if where_document == "":
        where_document = None
    elif where_document:
        try:
            where_document = json.loads(where_document)
        except json.JSONDecodeError as e:
            logging.error(f"[ChromaDB] Invalid where_document JSON: {e}")
            where_document = None

    # Handle where_filter
    if where_filter == "":
        where = None
    elif where_filter:
        try:
            where = json.loads(where_filter)
        except json.JSONDecodeError as e:
            logging.error(f"[ChromaDB] Invalid where_filter JSON: {e}")
            where = None

    try:
        if full_document_search == "Yes":
            if where and where_document:
                results = collection.get(include=["documents", "metadatas"], where=where, where_document=where_document)
            elif where:
                results = collection.get(include=["documents", "metadatas"], where=where)
            elif where_document:
                results = collection.get(include=["documents", "metadatas"], where_document=where_document)
            else:
                results = collection.get(include=["documents", "metadatas"])
        else:
            if where and where_document:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=max_results,
                    include=["documents", "metadatas"],
                    where=where,
                    where_document=where_document
                )
            elif where:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=max_results,
                    include=["documents", "metadatas"],
                    where=where
                )
            elif where_document:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=max_results,
                    include=["documents", "metadatas"],
                    where_document=where_document
                )
            elif filter_values:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=max_results,
                    include=["documents", "metadatas"],
                    where={"section": {"$in": filter_values}}
                )
            else:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=max_results,
                    include=["documents", "metadatas"]
                )
    except Exception as e:
        logging.error(f"Error retrieving documents: {e}")
        raise e

    return results

# -------------------------
# COMPONENT EXTRACTION FUNCTIONS
# -------------------------
def extract_components(query: str):
    """Extract components from query string"""
    if not isinstance(query, str):
        logging.error(f"Query is not a string in extract_components: {query} (type: {type(query)})")
        return {
            "document_id": None,
            "product_code": None,
            "field": None,
            "section": None,
            "question": str(query) if query is not None else None
        }

    try:
        document_match = re.search(r'from the (.*?) document', query, re.IGNORECASE)
        product_match = re.search(r'for product (.*?) under', query, re.IGNORECASE)
        field_match = re.search(r'Extract the (.*?) from', query, re.IGNORECASE)
        section_match = re.search(r'under (.*?) section', query, re.IGNORECASE)
        question_match = re.search(r'^(.*?) under', query, re.IGNORECASE)

        return {
            "document_id": document_match.group(1).strip() if document_match else None,
            "product_code": product_match.group(1).strip() if product_match else None,
            "field": field_match.group(1).strip() if field_match else None,
            "section": section_match.group(1).strip() if section_match else None,
            "question": question_match.group(1).strip() if question_match else None
        }
    except Exception as e:
        logging.error(f"Error in extract_components: {e}")
        return {
            "document_id": None,
            "product_code": None,
            "field": None,
            "section": None,
            "question": query
        }

# -------------------------
# PROMPT GENERATION FUNCTIONS
# -------------------------
def raw_prompt_template(context, prompt, role):
    """Generate raw prompt template"""
    return f"""{role}
Context:
{context}

{prompt}
"""


# -------------------------
# PDF TEXT EXTRACTION (PPWR)
# -------------------------
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2 if available; otherwise return empty string."""
    if not pdf_bytes:
        return ""
    if PyPDF2 is None:
        logging.warning("PyPDF2 not available; returning empty text for PDF")
        return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                texts.append("")
        return "\n".join(texts)
    except Exception as e:
        logging.error(f"Failed to extract PDF text: {e}")
        return ""
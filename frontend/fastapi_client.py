# fastapi_client.py

import os
import requests
import logging

# ==================== CONFIGURATION ====================
# Resolve FastAPI base URL:
# 1. Allow explicit environment override FASTAPI_BASE_URL
# 2. Default to container hostname when running under Docker (DOCKER environment var or presence of /.dockerenv)
# 3. Fallback to localhost for direct host/venv runs
_env_url = os.environ.get("FASTAPI_BASE_URL")
if _env_url:
    FASTAPI_BASE_URL = _env_url.rstrip('/')
else:
    _running_in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER') == '1'
    FASTAPI_BASE_URL = "http://pfas_fastapi:8000" if _running_in_docker else "http://127.0.0.1:8000"

# Create a dedicated logger for this module
logger = logging.getLogger(__name__)

def ingest_material_data(material_id):
    """
    Calls the FastAPI /ingest endpoint for a given material_id.
    Returns the full JSON response if successful, or None if an error occurred.
    Does NOT raise exceptions — returns None on any failure.
    """
    try:
        url = f"{FASTAPI_BASE_URL}/ingest"
        payload = {"material_id": material_id}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        # If the HTTP request was successful (status 200), parse and return JSON
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ HTTP {response.status_code} from FastAPI for material_id {material_id}: {response.text}")
            return None
    except Exception as e:
        # Log the exception but DO NOT crash. Return None to indicate failure.
        logger.error(f"❌ Exception calling FastAPI /ingest for material_id {material_id}: {e}")
        return None

def upload_supplier_declaration(file_path, sku=None, material_id=None, supplier_name=None, description=None, timeout=60):
    """Upload supplier declaration to backend FastAPI (PPWR storage).

    Returns JSON dict on success, or None on failure.
    """
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/supplier-declarations/upload"
        files = { 'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream') }
        data = {
            'sku': sku or '',
            'material_id': material_id or '',
            'supplier_name': supplier_name or '',
            'description': description or '',
        }
        resp = requests.post(url, files=files, data=data, timeout=timeout)
        if resp.status_code in (200,201):
            return resp.json()
        logger.error(f"❌ Backend upload failed ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Exception during backend upload: {e}")
        return None

def list_supplier_declarations(sku=None, material_id=None, include_archived=False, timeout=30):
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/supplier-declarations"
        params = {}
        if sku:
            params['sku'] = sku
        if material_id:
            params['material_id'] = material_id
        if include_archived:
            params['include_archived'] = 'true'
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"❌ Declarations list failed ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Exception listing declarations: {e}")
        return None

def assess_from_declaration(decl_id: int, material_id: str, timeout=120):
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/assess/from-declaration"
        data = { 'decl_id': str(decl_id), 'material_id': material_id }
        resp = requests.post(url, data=data, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"❌ Assess from declaration failed ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Exception assessing from declaration: {e}")
        return None

def get_assessments(material_id: str|None=None, timeout=30):
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/assessments"
        params = { 'material_id': material_id } if material_id else {}
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"❌ Get assessments failed ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Exception fetching assessments: {e}")
        return None

def map_supplier_declaration(decl_id: int, material_id: str, apply_to_duplicates: bool = False, scope: str = 'sku', timeout: int = 30):
    """
    POST to backend FastAPI /ppwr/supplier-declarations/map to persist mapping.
    Returns JSON on success or None on failure.
    """
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/supplier-declarations/map"
        data = {
            'decl_id': str(decl_id),
            'material_id': material_id or '',
            'apply_to_duplicates': 'true' if apply_to_duplicates else 'false',
            'scope': scope or 'sku'
        }
        resp = requests.post(url, data=data, timeout=timeout)
        # Try to parse JSON body if present so callers can inspect error messages
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        if resp.status_code in (200, 201):
            return body

        logger.error(f"❌ Map supplier declaration failed ({resp.status_code}): {resp.text}")
        # Return the parsed body (dict or text) so proxy can detect specific errors like 'Declaration not found'
        return body
    except Exception as e:
        logger.error(f"❌ Exception calling map endpoint: {e}")
        return None


def get_ppwr_evaluation_summary(timeout: int = 60):
    """Fetch summary stats and rows for PPWR evaluation UI."""
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/evaluation/summary"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"❌ Get PPWR evaluation summary failed ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Exception fetching PPWR evaluation summary: {e}")
        return None

def assess_with_files(bom_material_ids, files, timeout=180):
    """
    Run PPWR pipeline by posting local declaration bytes to FastAPI /ppwr/assess.
    bom_material_ids: list[str]
    files: list[(filename: str, bytes_obj: bytes, mime: str|None)]
    Returns parsed JSON on success or None on failure.
    """
    try:
        url = f"{FASTAPI_BASE_URL}/ppwr/assess"
        data = { 'bom_material_ids': ','.join(str(m).strip() for m in (bom_material_ids or []) if str(m).strip()) }
        files_payload = []
        for item in files or []:
            # Support tuples of len 2 or 3 = (fname, bytes[, mime])
            if isinstance(item, (list, tuple)):
                if len(item) >= 3:
                    fname, b, mime = item[0], item[1], item[2]
                else:
                    fname, b = item[0], item[1]
                    mime = None
            else:
                # Unexpected type; skip
                continue
            files_payload.append(('files', (fname or 'document.pdf', b, mime or 'application/pdf')))
        resp = requests.post(url, data=data, files=files_payload, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"❌ FastAPI /ppwr/assess failed ({resp.status_code}): {resp.text}")
        return None
    except Exception as e:
        logger.error(f"❌ Exception calling FastAPI /ppwr/assess: {e}")
        return None
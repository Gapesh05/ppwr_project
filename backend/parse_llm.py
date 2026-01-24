from typing import List, Any, Dict
import json
import re
import logging

logger = logging.getLogger(__name__)

def parse_llm_response(response: str) -> List[Dict[str, Any]]:
    """
    Parse an LLM response string into a list of dictionaries.
    Handles JSON arrays, single dictionaries, and embedded JSON snippets.
    """
    response = response.strip()

    if not response or response == "[]":
        return []

    # Step 1: Try direct JSON parse
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Step 2: Extract JSON object(s) with regex
    matches = re.findall(r'\{.*?\}', response, re.DOTALL)
    parsed = []
    for match in matches:
        try:
            obj = json.loads(match)
            if isinstance(obj, dict):
                parsed.append(obj)
        except json.JSONDecodeError:
            continue

    if parsed:
        return parsed

    logger.warning(f"⚠️ Could not parse LLM response: {response}")
    return []


def parse_ppwr_output(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize PPWR output into a consistent schema.

    Ensures keys and coercions:
      - material_id: str
      - supplier_name: str|None
      - declaration_date: str|None
      - ppwr_compliant: bool|None
      - packaging_recyclability: str|None
      - recycled_content_percent: float|None
      - restricted_substances: list[str]
      - notes: str|None
    """
    normalized = []
    for it in items:
        if not isinstance(it, dict):
            continue
        material_id = str(it.get('material_id') or '').strip()
        supplier_name = it.get('supplier_name') or None
        declaration_date = it.get('declaration_date') or None
        ppwr_val = it.get('ppwr_compliant')
        if isinstance(ppwr_val, str):
            ppwr_val = ppwr_val.strip().lower() in ('true', 'yes', 'y', '1')
        elif isinstance(ppwr_val, (int, float)):
            ppwr_val = bool(ppwr_val)

        packaging_recyclability = it.get('packaging_recyclability') or None
        rcp = it.get('recycled_content_percent')
        try:
            recycled_content_percent = float(rcp) if rcp is not None and str(rcp).strip() != '' else None
        except Exception:
            recycled_content_percent = None
        restricted = it.get('restricted_substances')
        if isinstance(restricted, list):
            restricted_substances = [str(x) for x in restricted]
        elif isinstance(restricted, str):
            # split by commas
            restricted_substances = [s.strip() for s in restricted.split(',') if s.strip()]
        else:
            restricted_substances = []
        notes = it.get('notes') or None

        # Regulatory mentions: expect list of {keyword, text, compliant?}
        mentions_raw = it.get('regulatory_mentions')
        regulatory_mentions: List[Dict[str, str]] = []
        if isinstance(mentions_raw, str):
            try:
                parsed_mentions = json.loads(mentions_raw)
                if isinstance(parsed_mentions, list):
                    mentions_raw = parsed_mentions
            except Exception:
                mentions_raw = [mentions_raw]
        if isinstance(mentions_raw, list):
            for m in mentions_raw:
                if isinstance(m, dict):
                    keyword = str(m.get('keyword') or '').strip()
                    text_val = str(m.get('text') or '').strip()
                    compliant_val = m.get('compliant')
                    if isinstance(compliant_val, str):
                        c_low = compliant_val.strip().lower()
                        compliant_val = True if c_low in {'true','yes','y','1'} else False if c_low in {'false','no','n','0'} else None
                    elif compliant_val not in (True, False):
                        compliant_val = None
                    if keyword or text_val:
                        entry = {'keyword': keyword, 'text': text_val}
                        if compliant_val in (True, False, None):
                            entry['compliant'] = compliant_val
                        regulatory_mentions.append(entry)
                elif isinstance(m, str):
                    mv = m.strip()
                    if mv:
                        regulatory_mentions.append({'keyword': '', 'text': mv, 'compliant': None})

        normalized.append({
            'material_id': material_id,
            'supplier_name': supplier_name,
            'declaration_date': declaration_date,
            'ppwr_compliant': ppwr_val if ppwr_val in (True, False) else None,
            'packaging_recyclability': packaging_recyclability,
            'recycled_content_percent': recycled_content_percent,
            'restricted_substances': restricted_substances,
            'notes': notes,
            'regulatory_mentions': regulatory_mentions,
        })

    return normalized

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
    """Normalize PPWR output to match ppwr_result table schema.
    
    Simplifies complex LLM extraction into evaluation-compatible format:
      - material_id: str (primary key)
      - supplier_name: str|None
      - cas_id: str|None
      - chemical: str (joined restricted substances or direct value)
      - concentration: float|None
      - status: 'Compliant'|'Non-Compliant'
      
    Rich metadata (packaging_recyclability, declaration_date, regulatory_mentions)
    is preserved in intermediate processing but not stored in ppwr_result.
    """
    normalized = []
    for it in items:
        if not isinstance(it, dict):
            continue
            
        material_id = str(it.get('material_id') or '').strip()
        supplier_name = it.get('supplier_name') or None
        cas_id = it.get('cas_id') or None
        
        # Parse ppwr_compliant boolean
        ppwr_val = it.get('ppwr_compliant')
        if isinstance(ppwr_val, str):
            ppwr_val = ppwr_val.strip().lower() in ('true', 'yes', 'y', '1')
        elif isinstance(ppwr_val, (int, float)):
            ppwr_val = bool(ppwr_val)
        
        # Extract and join restricted substances
        restricted = it.get('restricted_substances')
        if isinstance(restricted, list):
            restricted_substances = [str(x) for x in restricted]
        elif isinstance(restricted, str):
            restricted_substances = [s.strip() for s in restricted.split(',') if s.strip()]
        else:
            restricted_substances = []
        
        # Join to chemical string (primary display field)
        chemical = ', '.join(restricted_substances) if restricted_substances else it.get('chemical')
        
        # Extract concentration (try recycled_content_percent or direct concentration)
        concentration = it.get('concentration')
        if concentration is None:
            rcp = it.get('recycled_content_percent')
            try:
                concentration = float(rcp) if rcp is not None and str(rcp).strip() != '' else None
            except Exception:
                concentration = None
        
        # Map boolean to status enum
        if ppwr_val is None:
            # Infer from restricted substances presence
            ppwr_val = False if len(restricted_substances) > 0 else True
        status = 'Compliant' if ppwr_val else 'Non-Compliant'
        
        # Preserve rich metadata for logging/intermediate processing
        # (regulatory_mentions, packaging_recyclability, declaration_date, notes)
        # but not stored in ppwr_result table
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
        
        # Return simplified schema matching ppwr_result table
        normalized.append({
            'material_id': material_id,
            'supplier_name': supplier_name,
            'cas_id': cas_id,
            'chemical': chemical,
            'concentration': concentration,
            'status': status,
            'ppwr_compliant': ppwr_val,  # Preserved for intermediate logic
            'restricted_substances': restricted_substances,  # Preserved for mapping
            'regulatory_mentions': regulatory_mentions  # Preserved for logging
        })
    
    return normalized

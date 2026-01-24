import requests, json

BASE = 'http://127.0.0.1:8000'
MATS = ['A7658','A8362','B7346','B7462','C7236','C9347','D7282','E6236','E9371','F4373','F8990']

for m in MATS:
    r = requests.get(f"{BASE}/ppwr/assessments", params={'material_id': m}, timeout=20)
    if r.status_code != 200:
        print(f"{m}: error {r.status_code} {r.text}")
        continue
    body = r.json()
    items = body.get('assessments', []) if isinstance(body, dict) else []
    if not items:
        print(f"{m}: NO ASSESSMENT")
        continue
    a = items[0]
    restricted = json.loads(a.get('restricted_substances', '[]')) if isinstance(a.get('restricted_substances'), str) else (a.get('restricted_substances') or [])
    status = 'Compliant' if a.get('ppwr_compliant') else 'Non-Compliant'
    print(f"{m}: {status}, recyclability={a.get('packaging_recyclability')}, recycled%={a.get('recycled_content_percent')}, supplier={a.get('supplier_name')}, decl_date={a.get('declaration_date')}, source={a.get('source_path')}, restricted_count={len(restricted)}")

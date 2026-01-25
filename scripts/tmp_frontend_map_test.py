import os, requests, psycopg2

FRONTEND = 'http://127.0.0.1:5000'
PDF_PATH = r'C:\PPWR\NEW_FOLDER\PFAS_V0.2\New folder (2)\A7658_PETG.pdf'
SKU = 'A7658_SKU'
MATERIAL = 'A7658'

# 1) Upload via PPWR proxy (frontend -> backend)
print('Uploading declaration (page proxy)...')
files = {'file': (os.path.basename(PDF_PATH), open(PDF_PATH, 'rb'), 'application/pdf')}
data = {'sku': SKU, 'material': MATERIAL, 'supplier_name': 'Demo Supplier', 'description': 'Duplicate mapping test'}
r = requests.post(f"{FRONTEND}/ppwr/declarations/upload", files=files, data=data, timeout=60)
print('Upload status:', r.status_code)
print('Upload body (truncated):', r.text[:200])
resp = {}
print('Upload response:', resp)
backend_id = None
if isinstance(resp, dict) and resp.get('success') and isinstance(resp.get('backend'), dict):
    backend_id = resp['backend'].get('id')

if not backend_id:
    raise RuntimeError('No backend declaration id returned')
print('Backend decl_id:', backend_id)

# 2) Map with apply_to_duplicates=true, scope=all
print('Mapping (apply_to_duplicates=true, scope=all)...')
r2 = requests.post(f"{FRONTEND}/api/ppwr/supplier-declarations/map", data={
    'decl_id': str(backend_id), 'material_id': MATERIAL, 'apply_to_duplicates': 'true', 'scope': 'all'
}, timeout=30)
print('Map resp 1 status:', r2.status_code)
print('Map resp 1 body:', r2.text)

# 3) Map again with apply_to_duplicates=false, scope=sku
print('Mapping (apply_to_duplicates=false, scope=sku)...')
r3 = requests.post(f"{FRONTEND}/api/ppwr/supplier-declarations/map", data={
    'decl_id': str(backend_id), 'material_id': MATERIAL, 'apply_to_duplicates': 'false', 'scope': 'sku'
}, timeout=30)
print('Map resp 2 status:', r3.status_code)
print('Map resp 2 body:', r3.text)

# 4) Verify DB links for this decl_id
print('Verifying DB link rows...')
conn = psycopg2.connect(host='10.134.44.228', dbname='pfasdb', user='airadbuser', password='Password123')
cur = conn.cursor()
cur.execute('SELECT id, material_id, decl_id, sku, created_at FROM ppwr_material_declaration_links WHERE decl_id = %s ORDER BY id ASC', (int(backend_id),))
links = cur.fetchall()
print('Links:', links)
cur.close(); conn.close()
print('Done.')

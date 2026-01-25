import requests, sys
BASE='http://127.0.0.1:5001'
sku='102030'
print('Listing declarations for SKU', sku)
try:
    r = requests.get(f"{BASE}/api/supplier-declarations/{sku}?include_archived=0", timeout=10)
except Exception as e:
    print('GET request failed:', e)
    sys.exit(2)
print('GET status', r.status_code)
try:
    data = r.json()
    print('GET JSON:', data)
except Exception as e:
    print('GET parse failed:', e)
    print(r.text)
    sys.exit(3)
items = data.get('mappings', [])
if not items:
    print('No declarations found to delete')
    sys.exit(0)
first = items[0]
id = first.get('id')
print('First declaration id:', id)
# Attempt delete
try:
    d = requests.delete(f"{BASE}/api/supplier-declarations/{id}?sku={sku}", timeout=10)
    print('DELETE status', d.status_code)
    try:
        print('DELETE JSON:', d.json())
    except Exception:
        print('DELETE body:', d.text)
except Exception as e:
    print('DELETE request failed:', e)
    sys.exit(4)

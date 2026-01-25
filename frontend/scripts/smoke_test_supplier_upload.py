import os
import json
import requests
from io import BytesIO

# Allow override via PFAS_BASE env var, e.g., http://127.0.0.1:5050
BASE = os.environ.get('PFAS_BASE', 'http://localhost:5000')

def main():
    sku = 'TESTSKU123'
    material = 'MAT-1'
    # Prefer uploading the provided sample PDF if present; else a tiny text
    pdf_path = os.path.join(os.path.dirname(__file__), '..', 'tmp_uploads', '8025_CORRUGATED CARTON.pdf')
    pdf_path = os.path.abspath(pdf_path)
    if os.path.exists(pdf_path):
        print('Using sample PDF:', pdf_path)
        files = {
            'file': ('8025_CORRUGATED CARTON.pdf', open(pdf_path, 'rb'), 'application/pdf')
        }
    else:
        files = {
            'file': ('test.txt', b'hello world', 'text/plain')
        }
    data = {
        'sku': sku,
        'material': material,
        'metadata': json.dumps({'note': 'smoke'})
    }
    r = requests.post(f'{BASE}/api/assessment-upload', files=files, data=data, timeout=20)
    print('UPLOAD status:', r.status_code)
    print('UPLOAD body:', r.text)
    r.raise_for_status()
    resp = r.json()
    decl_id = resp.get('id')

    # List
    r2 = requests.get(f'{BASE}/api/supplier-declarations/{sku}', timeout=20)
    print('LIST status:', r2.status_code)
    print('LIST body:', r2.text)
    r2.raise_for_status()

    # Download
    r3 = requests.get(f'{BASE}/supplier-declaration/{decl_id}/download', timeout=20)
    print('DOWNLOAD status:', r3.status_code)
    print('DOWNLOAD content-type:', r3.headers.get('Content-Type'))
    print('DOWNLOAD length:', len(r3.content))
    r3.raise_for_status()

if __name__ == '__main__':
    main()

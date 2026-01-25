import os
import io
import json
from werkzeug.datastructures import FileStorage

from app import app, db


def run_internal_test():
    sku = 'TESTSKU123'
    material = 'MAT-1'

    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tmp_uploads', '8025_CORRUGATED CARTON.pdf'))
    if not os.path.exists(pdf_path):
        raise SystemExit(f"Sample PDF not found at {pdf_path}")

    with app.app_context():
        client = app.test_client()

        with open(pdf_path, 'rb') as f:
            data = {
                'sku': sku,
                'material': material,
                'metadata': json.dumps({'note': 'smoke'})
            }
            # The 'file' field must be a (file-object, filename) tuple
            data['file'] = (f, '8025_CORRUGATED CARTON.pdf')

            resp = client.post('/api/assessment-upload', data=data, content_type='multipart/form-data')
            print('UPLOAD status:', resp.status_code)
            print('UPLOAD body:', resp.data.decode('utf-8', errors='ignore'))
            if resp.status_code not in (200, 201):
                raise SystemExit('Upload failed')

        # List declarations
        r2 = client.get(f'/api/supplier-declarations/{sku}')
        print('LIST status:', r2.status_code)
        print('LIST body:', r2.data.decode('utf-8', errors='ignore'))
        if r2.status_code != 200:
            raise SystemExit('List failed')

        payload = r2.get_json(silent=True) or {}
        items = payload.get('declarations') or payload.get('items') or []
        if not items:
            raise SystemExit('No declarations returned for SKU')
        decl_id = items[0]['id']

        # Download
        r3 = client.get(f'/supplier-declaration/{decl_id}/download')
        print('DOWNLOAD status:', r3.status_code)
        print('DOWNLOAD content-type:', r3.headers.get('Content-Type'))
        print('DOWNLOAD length:', len(r3.data))
        if r3.status_code != 200:
            raise SystemExit('Download failed')


if __name__ == '__main__':
    run_internal_test()

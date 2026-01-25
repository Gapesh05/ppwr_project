import os
import sys
from io import BytesIO

# Use local sqlite DB to avoid external dependencies for test
os.environ['DATABASE_URL'] = 'sqlite:///test_frontend.db'

# Ensure frontend/ is importable so `from config import Config` resolves to frontend/config.py
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from frontend.app import app, db, PFASBOM


def main():
    with app.app_context():
        db.create_all()
        sku = 'SKU_TEST_001'
        material = 'MAT123'
        if not db.session.query(PFASBOM).filter_by(sku=sku, material=material).first():
            db.session.add(PFASBOM(
                sku=sku,
                component='C1',
                subcomponent='S1',
                material=material,
                product='Test Product',
                component_description='Comp',
                subcomponent_description='Sub',
                material_name='Mat Name',
                portal_name='Portal',
                region='EU',
                assessment='PFAS',
                flag=False
            ))
            db.session.commit()

    client = app.test_client()

    pdf_bytes = b'%PDF-1.4\n%Test PDF content for upload'
    data = {
        'sku': 'SKU_TEST_001',
        'material': 'MAT123',
        'files': (BytesIO(pdf_bytes), 'MAT123_test.pdf')
    }

    resp = client.post('/api/supplier-declarations/upload', data=data, content_type='multipart/form-data')
    print('STATUS', resp.status_code)
    try:
        print('BODY', resp.json)
    except Exception:
        print('BODY (raw)', resp.data[:200])

    if resp.status_code in (200, 201):
        j = None
        try:
            j = resp.json
        except Exception:
            pass
        if j and j.get('uploaded'):
            decl_id = j['uploaded'][0]['id']
            dl = client.get(f'/supplier-declaration/{decl_id}/download')
            print('DL_STATUS', dl.status_code)
            print('DL_CT', dl.headers.get('Content-Type'))
            print('DL_LEN', len(dl.data))


if __name__ == '__main__':
    main()

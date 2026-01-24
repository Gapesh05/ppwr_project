import os
import sys
from io import BytesIO

# Use local sqlite DB for isolation
os.environ['DATABASE_URL'] = 'sqlite:///test_frontend.db'

# Ensure frontend/ is importable
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

# Load app explicitly from NEW_FOLDER path to avoid picking up a duplicate workspace copy
import importlib.util
app_path = os.path.join(FRONTEND_DIR, 'app.py')
app_spec = importlib.util.spec_from_file_location('frontend_app', app_path)
app_module = importlib.util.module_from_spec(app_spec)
app_spec.loader.exec_module(app_module)
app = app_module.app
db = app_module.db
PFASBOM = app_module.PFASBOM
import types
models_path = os.path.join(FRONTEND_DIR, 'models.py')
spec = importlib.util.spec_from_file_location('frontend_models', models_path)
fmodels = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmodels)
LinkModel = fmodels.PPWRMaterialDeclarationLink


def main():
    with app.app_context():
        db.create_all()
        sku = 'SKU_TEST_002'
        material = 'MAT456'
        # Seed BOM row so upload passes validation
        if not db.session.query(PFASBOM).filter_by(sku=sku, material=material).first():
            db.session.add(PFASBOM(
                sku=sku,
                component='C2',
                subcomponent='S2',
                material=material,
                product='Test Product 2',
                component_description='Comp2',
                subcomponent_description='Sub2',
                material_name='Mat Name 2',
                portal_name='Portal',
                region='EU',
                assessment='PFAS',
                flag=False
            ))
            db.session.commit()

    client = app.test_client()

    # Upload a declaration
    pdf_bytes = b'%PDF-1.4\n%Test PDF for mapping'
    data = {
        'sku': 'SKU_TEST_002',
        'material': 'MAT456',
        'files': (BytesIO(pdf_bytes), 'MAT456_decl.pdf')
    }
    resp = client.post('/api/supplier-declarations/upload', data=data, content_type='multipart/form-data')
    print('UPLOAD_STATUS', resp.status_code)
    try:
        print('UPLOAD_BODY', resp.json)
    except Exception:
        print('UPLOAD_BODY (raw)', resp.data[:200])

    assert resp.status_code in (200, 201), 'Upload failed'
    uploaded = resp.json.get('uploaded') or []
    assert uploaded, 'No uploaded items returned'
    decl_id = uploaded[0]['id']

    # Invoke frontend mapping route (robust one that persists local links)
    map_data = {
        'decl_id': str(decl_id),
        'material_id': 'MAT456',
        'apply_to_duplicates': 'false',
        'scope': 'sku'
    }
    m = client.post('/api/ppwr/supplier-declarations/map', data=map_data)
    print('MAP_STATUS', m.status_code)
    try:
        print('MAP_BODY', m.json)
    except Exception:
        print('MAP_BODY (raw)', m.data[:200])

    assert m.status_code == 200 and m.json and m.json.get('success'), 'Mapping failed'

    # Verify link persisted locally
    with app.app_context():
        link = db.session.query(LinkModel).filter_by(material_id='MAT456', decl_id=decl_id).first()
        print('LINK_FOUND', bool(link))
        assert link is not None, 'Local link not created'


if __name__ == '__main__':
    main()

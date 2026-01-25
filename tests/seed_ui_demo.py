import os, sys
# Use a local sqlite DB for the demo UI
os.environ['DATABASE_URL'] = 'sqlite:///ui_demo.db'

# Ensure frontend import
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from frontend.app import app, db, PFASBOM

SKU = 'DEMO_SKU_001'
MAT = 'DEMO_MAT001'

with app.app_context():
    db.create_all()
    if not db.session.query(PFASBOM).filter_by(sku=SKU, material=MAT).first():
        db.session.add(PFASBOM(
            sku=SKU,
            component='COMP',
            subcomponent='SUBC',
            material=MAT,
            product='Demo Product',
            component_description='Component',
            subcomponent_description='Subcomponent',
            material_name='Material Name',
            portal_name='Portal',
            region='EU',
            assessment='PFAS',
            flag=False
        ))
        db.session.commit()
print('Seeded BOM row for', SKU, MAT)

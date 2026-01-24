import sys, os, re
from datetime import datetime

# Ensure frontend is importable
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app, db
from models import PFASBOM

TEST_SKU = 'SKU_PERSIST_TEST'

def main():
    with app.app_context():
        # Clean any existing test data
        db.session.query(PFASBOM).filter_by(sku=TEST_SKU).delete()
        db.session.commit()

        # Insert minimal BOM rows with uploaded_at set
        now = datetime.utcnow()
        rows = [
            PFASBOM(
                sku=TEST_SKU,
                product='Persist Product',
                component='C1',
                component_description='Comp Desc 1',
                subcomponent='S1',
                subcomponent_description='Sub Desc 1',
                material='M1',
                material_name='Mat 1',
                portal_name='SAP',
                region='Global',
                assessment='PFAS',
                uploaded_at=now,
            ),
            PFASBOM(
                sku=TEST_SKU,
                product='Persist Product',
                component='C2',
                component_description='Comp Desc 2',
                subcomponent='S2',
                subcomponent_description='Sub Desc 2',
                material='M2',
                material_name='Mat 2',
                portal_name='SAP',
                region='Global',
                assessment='PFAS',
                uploaded_at=now,
            ),
        ]
        for r in rows:
            db.session.add(r)
        db.session.commit()

        # Expected timestamp format used by index() when formatting persisted value
        expected = now.strftime('%Y-%m-%d %H:%M:%S UTC')

        # Hit the dashboard without starting a server
        client = app.test_client()
        resp = client.get('/')
        html = resp.get_data(as_text=True)

        # Look for the SKU row and the timestamp string
        ok_sku = TEST_SKU in html
        ok_time = expected in html

        # Always show a snippet of the table for visual confirmation
        m = re.search(r'<tbody[\s\S]*?</tbody>', html)
        if m:
            snippet = m.group(0)
            print('--- TABLE SNIPPET START ---')
            print(snippet[:2000])
            print('--- TABLE SNIPPET END ---')

        if ok_sku and ok_time:
            print('SMOKE_OK: BOM_time rendered and persisted for', TEST_SKU, expected)
            return 0
        else:
            # Provide some debug context
            print('SMOKE_FAIL')
            print('Found SKU in HTML:', ok_sku)
            print('Found timestamp in HTML:', ok_time)
            return 1

if __name__ == '__main__':
    raise SystemExit(main())

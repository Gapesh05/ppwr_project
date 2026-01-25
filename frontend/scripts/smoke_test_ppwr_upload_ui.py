import sys, os, re
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import app, db
from models import PFASBOM

SKU_EMPTY = 'SKU_PPWR_NO_UPLOAD'
SKU_WITH_UPLOAD = 'SKU_PPWR_WITH_UPLOAD'

def has_upload_time_snippet(html, sku):
    # Find the PPWR tab body
    mtab = re.search(r'id=\"ppwrTableBody\"[\s\S]*?</tbody>', html)
    if not mtab:
        return False
    tbody = mtab.group(0)
    # Narrow down rows for the sku
    rows = [seg for seg in tbody.split('</tr>') if sku in seg]
    if not rows:
        return False
    segment = rows[0]
    # Look for the small upload-time div in the segment
    return ('class="small text-muted upload-time' in segment)

with app.app_context():
    db.create_all()
    # Clean skus
    PFASBOM.query.filter(PFASBOM.sku.in_([SKU_EMPTY, SKU_WITH_UPLOAD])).delete(synchronize_session=False)
    db.session.commit()

    # Insert rows for SKU with no uploaded_at
    r_empty = PFASBOM(
        sku=SKU_EMPTY,
        product='PPWR Test',
        component='C0',
        component_description='Comp 0',
        subcomponent='S0',
        subcomponent_description='Sub 0',
        material='M0',
        material_name='Mat 0',
        portal_name='SAP',
        region='Global',
        assessment='PPWR',
        uploaded_at=None,
    )
    db.session.add(r_empty)

    # Insert rows for SKU with uploaded_at
    now = datetime.utcnow()
    r_up = PFASBOM(
        sku=SKU_WITH_UPLOAD,
        product='PPWR Test',
        component='C1',
        component_description='Comp 1',
        subcomponent='S1',
        subcomponent_description='Sub 1',
        material='M1',
        material_name='Mat 1',
        portal_name='SAP',
        region='Global',
        assessment='PPWR',
        uploaded_at=now,
    )
    db.session.add(r_up)
    db.session.commit()

    client = app.test_client()
    # Hit PPWR assessment route (auto-activates PPWR tab)
    resp = client.get(f'/ppwr-assessment/{SKU_EMPTY}')
    html_empty = resp.get_data(as_text=True)
    resp2 = client.get(f'/ppwr-assessment/{SKU_WITH_UPLOAD}')
    html_up = resp2.get_data(as_text=True)

    empty_has_time = has_upload_time_snippet(html_empty, SKU_EMPTY)
    up_has_time = has_upload_time_snippet(html_up, SKU_WITH_UPLOAD)

    print('PPWR_NO_UPLOAD_has_time:', empty_has_time)
    print('PPWR_WITH_UPLOAD_has_time:', up_has_time)

    # Basic expectations
    if not empty_has_time and up_has_time:
        print('SMOKE_OK: PPWR upload timestamp hidden before upload and shown after upload')
        raise SystemExit(0)
    else:
        print('SMOKE_FAIL')
        # Print small excerpts to help debug
        for label, html in [('EMPTY', html_empty), ('WITH_UPLOAD', html_up)]:
            print('---', label, 'PPWR TABLE SNIPPET ---')
            mtab = re.search(r'id=\"ppwrTableBody\"[\s\S]*?</tbody>', html)
            if mtab:
                print(mtab.group(0)[:2000])
        raise SystemExit(1)

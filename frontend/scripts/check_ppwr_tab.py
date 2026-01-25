import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import app

sku = os.environ.get('PPWR_SKU', '102030')
with app.test_client() as c:
    resp = c.get(f'/assessment/{sku}', follow_redirects=True)
    html = resp.get_data(as_text=True)
    has_tab = ('id="ppwrTab"' in html) or ('data-bs-target="#ppwrTab"' in html) or ('id="ppwrTableBody"' in html)
    has_modal = ('id="multiUploadModal"' in html) and ('id="mu-apply-duplicates"' in html)
    print('HTTP_STATUS', resp.status_code)
    print('PPWR_TAB_PRESENT' if has_tab else 'PPWR_TAB_MISSING')
    print('PPWR_UPLOAD_MODAL_PRESENT' if has_modal else 'PPWR_UPLOAD_MODAL_MISSING')
    sys.exit(0 if has_tab and has_modal else 2)

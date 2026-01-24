import re
from app import app

# Verify that the assessment page renders the multi-upload modal content
# and the apply-to-duplicates checkbox.

with app.test_client() as c:
    resp = c.get('/assessment/102030', follow_redirects=True)
    html = resp.get_data(as_text=True)
    status = resp.status_code

    has_bootstrap_modal = 'id="multiUploadModal"' in html
    has_checkbox = 'id="mu-apply-duplicates"' in html
    has_drop_zone = 'id="mu-drop-zone"' in html

    print(f"HTTP_STATUS {status}")
    print("HAS_MULTI_UPLOAD_MODAL" if has_bootstrap_modal else "MISSING_MULTI_UPLOAD_MODAL")
    print("HAS_APPLY_DUPLICATES_CHECKBOX" if has_checkbox else "MISSING_APPLY_DUPLICATES_CHECKBOX")
    print("HAS_DROP_ZONE" if has_drop_zone else "MISSING_DROP_ZONE")

import os, sys, io, json, datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import app, db
from models import SupplierDeclaration
from werkzeug.datastructures import FileStorage

SKU = 'TOASTSKU1'

HTML_EXPORT = os.path.join(os.path.dirname(__file__), '..', 'logs', 'supplier_declaration_toast_demo.html')

# Minimal JS to render a toast similar to existing showToast implementation
TOAST_WRAPPER = """
<!DOCTYPE html><html><head><meta charset='utf-8'><title>Toast Demo</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css' rel='stylesheet'>
<style>.toast{border-radius:12px;margin:8px;animation:fadeIn .3s}.toast-body{font-size:0.9rem} @keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}} .container{padding:2rem}</style>
</head><body><div class='container'><h4>Supplier Declaration Upload Toast Demo</h4><div id='toastHost'></div></div>
<script>
function injectToast(html,type){const d=document.createElement('div');d.className=`toast show bg-${type} text-white`;d.innerHTML='<div class="d-flex p-3"><div class="toast-body">'+html+'</div></div>';document.getElementById('toastHost').appendChild(d);} 
// SUCCESS_TOAST
injectToast(%s,'success');
// ERROR_TOAST
injectToast(%s,'danger');
</script></body></html>
"""

def build_file(filename: str, content: bytes, mimetype: str):
    return FileStorage(stream=io.BytesIO(content), filename=filename, content_type=mimetype)

with app.app_context():
    client = app.test_client()

    # Prepare two fake files (one allowed, one with bad extension to force an error)
    pdf_file = build_file('example.pdf', b'%PDF-1.4 test pdf content', 'application/pdf')
    bad_file = build_file('malware.exe', b'MZ\x00\x00', 'application/octet-stream')

    data = {
        'sku': SKU,
        'supplier_name': 'Demo Supplier',
        'description': 'Automated toast test',
        'files': [pdf_file, bad_file]
    }

    # Post multipart form
    resp = client.post('/api/supplier-declarations/upload', data=data, content_type='multipart/form-data')
    j = resp.get_json() or {}

    success_uploaded = j.get('total_uploaded', 0)
    failed_errors = j.get('total_errors', 0)
    ts = j.get('upload_time') or (j.get('uploaded')[0]['upload_date'] if j.get('uploaded') else None)
    # Format timestamp
    ts_display = ''
    if ts:
        try:
            dt = datetime.datetime.fromisoformat(ts.replace('Z',''))
            ts_display = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except Exception:
            ts_display = ts

    success_html = json.dumps(f"<i class='bi bi-cloud-check'></i> <strong>{success_uploaded} file(s) uploaded successfully</strong>" + (f"<div class='small text-muted'><i class='bi bi-clock-history me-1'></i>{ts_display}</div>" if ts_display else '') )

    if failed_errors:
        error_html_raw = f"<i class='bi bi-exclamation-circle'></i> <strong>{failed_errors} file(s) failed</strong>"
    else:
        error_html_raw = "<i class='bi bi-exclamation-circle'></i> <strong>No failures</strong>"
    error_html = json.dumps(error_html_raw)

    os.makedirs(os.path.dirname(HTML_EXPORT), exist_ok=True)
    with open(HTML_EXPORT, 'w', encoding='utf-8') as f:
        f.write(TOAST_WRAPPER % (success_html, error_html))

    print('UPLOAD_STATUS:', resp.status_code)
    print('JSON_RESPONSE:', j)
    print('EXPORTED_HTML:', HTML_EXPORT)

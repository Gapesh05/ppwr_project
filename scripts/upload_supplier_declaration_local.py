import sys
import os
import hashlib
from datetime import datetime

HERE = os.path.dirname(os.path.dirname(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from backend import models
except Exception as e:
    print('ERROR importing backend.models:', e)
    raise


def detect_doc_type(fname):
    ext = os.path.splitext(fname.lower())[1]
    if ext == '.pdf':
        return 'pdf'
    if ext in ('.docx', '.doc'):
        return 'docx'
    if ext in ('.xlsx', '.xls'):
        return 'xlsx'
    if ext in ('.txt', '.csv'):
        return 'txt'
    return None


def main(path):
    if not os.path.exists(path):
        print('File not found:', path)
        return 2
    with open(path, 'rb') as f:
        data = f.read()
    fname = os.path.basename(path)
    doc_type = detect_doc_type(fname)
    file_size = len(data)
    file_hash = hashlib.sha256(data).hexdigest()

    decl = models.SupplierDeclaration(
        sku=None,
        material_id=None,
        original_filename=fname,
        document_type=doc_type,
        upload_date=datetime.utcnow(),
        file_size=file_size,
        file_data=data,
        supplier_name=None,
        description='Uploaded via scripts/upload_supplier_declaration_local.py',
        metadata_json=None,
        is_archived=False,
        file_hash=file_hash
    )

    session = models.SessionLocal()
    try:
        session.add(decl)
        session.flush()
        print('Inserted id:', decl.id)
        session.commit()
        print('Commit OK')
        return 0
    except Exception as e:
        session.rollback()
        print('DB error:', e)
        return 3
    finally:
        session.close()


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), 'tmp_ppwr_decl.txt')
    print('Uploading file:', arg)
    sys.exit(main(arg))

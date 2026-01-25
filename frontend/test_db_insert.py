from app import app
from models import db, SupplierDeclaration

with app.app_context():
    s = SupplierDeclaration(
        sku='TEST-SKU-VERIFY',
        document_type='pdf',
        original_filename='test.pdf',
        storage_filename='test.pdf',
        file_path='C:/tmp/test.pdf',
        file_size=123
    )
    db.session.add(s)
    db.session.commit()
    print('INSERT_OK', s.id)

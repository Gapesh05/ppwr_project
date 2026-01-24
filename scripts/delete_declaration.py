import sys

if len(sys.argv) < 2:
    print('Usage: python delete_declaration.py <id>')
    sys.exit(2)

id_to_delete = int(sys.argv[1])

# Ensure repo root on path
import os
HERE = os.path.dirname(os.path.dirname(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from backend import models

session = models.SessionLocal()
try:
    row = session.query(models.SupplierDeclaration).filter(models.SupplierDeclaration.id == id_to_delete).first()
    if not row:
        print(f'Row id={id_to_delete} not found in supplier_declarations_backend')
        sys.exit(0)
    print('Found row:', row.id, row.original_filename)
    session.delete(row)
    session.commit()
    print('Deleted row id=', id_to_delete)
finally:
    session.close()

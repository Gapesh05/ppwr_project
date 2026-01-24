from backend import models
from sqlalchemy import text

engine = models.engine
print('Using engine:', engine)
# Count rows first
with engine.connect() as conn:
    res = conn.execute(text('SELECT COUNT(*) FROM supplier_declarations_backend'))
    total = res.scalar()
print('Rows in supplier_declarations_backend:', total)
if total == 0:
    print('No rows to update.')
else:
    print('Updating blob/storage fields (file_data, file_size, file_hash, storage_filename, file_path) ...')
    with engine.begin() as conn:
        r = conn.execute(text(
            """
            UPDATE supplier_declarations_backend
            SET file_data = NULL,
                file_size = 0,
                file_hash = NULL,
                storage_filename = NULL,
                file_path = NULL
            """
        ))
    print('Update executed. Note: transaction committed.')
    # Recount
    with engine.connect() as conn:
        res2 = conn.execute(text('SELECT COUNT(*) FROM supplier_declarations_backend WHERE file_data IS NOT NULL'))
        remaining = res2.scalar()
    print('Rows still having file_data non-null after update:', remaining)

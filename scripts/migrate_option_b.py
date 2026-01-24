from sqlalchemy import create_engine, text
from frontend.config import Config

def main():
    eng = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    print('Starting Option B migration: supplier_declarations -> PK(material_id)')
    with eng.begin() as conn:
        conn.execute(text('ALTER TABLE supplier_declarations ADD COLUMN IF NOT EXISTS material_id VARCHAR(100)'))
        print('OK: add material_id')
        conn.execute(text('UPDATE supplier_declarations SET material_id = material WHERE material_id IS NULL AND material IS NOT NULL'))
        print('OK: backfill from material')
        # Drop FK to old PK if such a table exists
        conn.execute(text('ALTER TABLE IF EXISTS upload_audit_logs DROP CONSTRAINT IF EXISTS upload_audit_logs_document_id_fkey'))
        print('OK: drop old FK if present')
        conn.execute(text('ALTER TABLE supplier_declarations DROP CONSTRAINT IF EXISTS supplier_declarations_pkey CASCADE'))
        print('OK: drop old PK')
        conn.execute(text('ALTER TABLE supplier_declarations ALTER COLUMN material_id SET NOT NULL'))
        print('OK: set NOT NULL')
        conn.execute(text('ALTER TABLE supplier_declarations ADD CONSTRAINT supplier_declarations_pkey PRIMARY KEY (material_id)'))
        print('OK: add new PK')
        conn.execute(text('ALTER TABLE supplier_declarations DROP COLUMN IF EXISTS id'))
        print('OK: drop id')
        conn.execute(text('ALTER TABLE supplier_declarations DROP COLUMN IF EXISTS material'))
        print('OK: drop material')
    print('Migration complete.')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Backup and optionally delete all rows from supplier_declarations_backend.
Usage:
  # Dry-run: create backup CSV but don't delete
  python scripts/clear_supplier_declarations_backend.py

  # Delete after backup (use with care!)
  python scripts/clear_supplier_declarations_backend.py --yes

The script uses the SQLAlchemy engine in `backend.models` (so it will use the same DB URL).
"""
import sys
import os
import csv
import datetime

# Ensure repo root is on sys.path so we can import backend.models
HERE = os.path.dirname(os.path.dirname(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from backend import models
    from sqlalchemy import text
except Exception as e:
    print("ERROR: failed to import backend.models; are you running from the repo root and is a venv activated?", e)
    raise

DRY_RUN = '--yes' not in sys.argv

def backup_and_optionally_delete():
    engine = models.engine
    backup_dir = os.path.join(HERE, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'supplier_declarations_backup_{ts}.csv')

    print(f"Connecting to database using engine: {engine}")

    # Read all rows
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM supplier_declarations_backend")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    print(f"Fetched {len(rows)} rows from supplier_declarations_backend")

    # Write CSV backup
    with open(backup_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            # Normalize bytes to repr to avoid binary write issues
            out = []
            for v in r:
                if v is None:
                    out.append('')
                elif isinstance(v, (bytes, bytearray)):
                    # do not dump entire binary; indicate presence and length
                    out.append(f'<BINARY {len(v)} bytes>')
                else:
                    out.append(str(v))
            writer.writerow(out)

    print(f"Backup written to: {backup_file}")

    if DRY_RUN:
        print("Dry run (no delete). To delete, re-run with --yes")
        return

    # Confirm before deleting
    print("Deleting all rows from supplier_declarations_backend...")
    with engine.begin() as conn2:
        conn2.execute(text("DELETE FROM supplier_declarations_backend"))
    print("Delete completed.")

if __name__ == '__main__':
    try:
        backup_and_optionally_delete()
    except Exception as e:
        print('ERROR:', e)
        raise

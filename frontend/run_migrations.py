import os
import sys
from pathlib import Path
import psycopg2

# Allow importing Config
sys.path.append(str(Path(__file__).parent))
from config import Config

def apply_file(dsn: str, sql_text: str, name: str):
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql_text)
        print(f"Applied migration: {name}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main():
    migrations_dir = Path(__file__).parent / 'db_migrations'
    files = sorted([p for p in migrations_dir.glob('*.sql')])
    if not files:
        print("No migration files found.")
        return 0

    dsn = Config.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to DB: {dsn}")
    failures = []
    for p in files:
        try:
            sql_text = p.read_text(encoding='utf-8')
            apply_file(dsn, sql_text, p.name)
        except Exception as e:
            print(f"Failed applying {p.name}: {e}")
            failures.append(p.name)
            continue
    if failures:
        print(f"Completed with failures in: {', '.join(failures)}")
    else:
        print("All migrations applied.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
import sys
from pathlib import Path


def main():
    print("Migrations disabled: using SQLite with SQLAlchemy create_all().")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

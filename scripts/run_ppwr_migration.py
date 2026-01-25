import psycopg2
from pathlib import Path

def main():
    sql_path = Path('backend/db_migrations/010_create_ppwr_bom.sql')
    sql = sql_path.read_text()
    conn = psycopg2.connect(host='10.134.44.228', user='airadbuser', password='Password123', dbname='pfasdb')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print('Applied 010_create_ppwr_bom.sql')

if __name__ == '__main__':
    main()

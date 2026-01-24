import psycopg2

HOST = '10.134.44.228'
DB = 'pfasdb'
USER = 'airadbuser'
PASSWORD = 'Password123'

conn = psycopg2.connect(host=HOST, dbname=DB, user=USER, password=PASSWORD)
cur = conn.cursor()
cur.execute("SELECT sku, material FROM pfas_bom LIMIT 10;")
rows = cur.fetchall()
print('PFAS_BOM sample:', rows)
cur.execute("SELECT material_id, COUNT(*) FROM ppwr_bom GROUP BY material_id HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 10;")
rows2 = cur.fetchall()
print('PPWR_BOM duplicates:', rows2)
cur.close()
conn.close()

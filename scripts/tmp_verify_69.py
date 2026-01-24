from backend import models
from sqlalchemy import text
conn = models.engine.connect()
res = conn.execute(text("SELECT id FROM supplier_declarations_backend WHERE id = 69"))
print('SELECT result for id=69:', res.fetchone())
conn.close()

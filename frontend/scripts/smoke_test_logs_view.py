import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import app

with app.app_context():
    client = app.test_client()
    resp = client.get('/logs')
    html = resp.get_data(as_text=True)
    print('LOGS_VIEW_LEN:', len(html))
    # Print a small snippet
    print('--- LOGS SNIPPET ---')
    print(html[:800])
    print('--- END ---')

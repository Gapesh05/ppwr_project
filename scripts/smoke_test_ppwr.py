import requests
import sys

def main(base_url: str, material_ids: list[str], pdf_path: str):
    files = [('files', (pdf_path.split('/')[-1], open(pdf_path, 'rb'), 'application/pdf'))]
    data = {'bom_material_ids': ','.join(material_ids)}
    r = requests.post(f"{base_url}/ppwr/assess", files=files, data=data, timeout=60)
    print("POST /ppwr/assess:", r.status_code, r.text)
    rid = material_ids[0]
    g = requests.get(f"{base_url}/ppwr/assessments", params={'material_id': rid}, timeout=30)
    print("GET /ppwr/assessments:", g.status_code, g.text)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python scripts/smoke_test_ppwr.py <BASE_URL> <material_id1,material_id2> <PDF_PATH>")
        sys.exit(1)
    base = sys.argv[1]
    mids = sys.argv[2].split(',')
    pdf = sys.argv[3]
    main(base, mids, pdf)

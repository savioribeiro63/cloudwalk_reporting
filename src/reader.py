import csv

def read_transactions(path: str):
    rows = []
    with open(path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
    return rows

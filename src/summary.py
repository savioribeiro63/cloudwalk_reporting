import json

def build_summary_metrics(rows_in: int, rows_out: int, extra_metrics: dict):
    metrics = {
        "rows_in": rows_in,
        "rows_out": rows_out
    }
    metrics.update(extra_metrics or {})
    metrics["rows_excluded"] = rows_in - rows_out - metrics.get("duplicates_removed", 0)
    return metrics

def write_summary_json(metrics: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    return path

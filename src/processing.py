import os
from datetime import datetime
from .reader import read_transactions
from .normalizer import normalize_and_filter
from .xml_builder import build_xml_report
from .summary import build_summary_metrics, write_summary_json
from .emailer import send_report_email

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def month_to_folder(month: str) -> str:
    return month.replace("-", "")

def process_month(month: str, input_path: str, output_base: str, send_email: bool = False):
    try:
        # Read
        rows = read_transactions(input_path)
        # Normalize + Filter
        norm_rows, metrics = normalize_and_filter(rows, month)
        metrics = build_summary_metrics(rows_in=len(rows), rows_out=len(norm_rows), extra_metrics=metrics)

        # Outputs
        out_dir = os.path.join(output_base, month_to_folder(month))
        ensure_dir(out_dir)
        report_path = os.path.join(out_dir, "report.xml")
        build_xml_report(month=month, rows=norm_rows, out_path=report_path)

        summary_path = os.path.join(out_dir, "summary.json")
        write_summary_json(metrics, summary_path)

        email_result = None
        if send_email:
            email_result = send_report_email(month=month, metrics=metrics, attachment_path=report_path, out_dir=out_dir)

        return {"status": "ok", "report_path": report_path, "summary_path": summary_path, "metrics": metrics, "email_result": email_result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

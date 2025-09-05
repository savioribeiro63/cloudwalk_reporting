import os, smtplib, ssl, traceback
from email.message import EmailMessage
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict

def _safe_decimal(v) -> Decimal:
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")

def _analytics_from_xml(attachment_path: str):
    """
    Parse XML and return:
      - totals_by_category: {"DEBIT": Decimal(...), "CREDIT": Decimal(...), ...}
      - counts_by_category: {"DEBIT": int, "CREDIT": int, ...}
      - counts_by_status:   {"approved": int, "chargeback": int, ...}  # lower-case
      - currency: str (default BRL)
      - count: total transactions in XML
    """
    totals_by_category = defaultdict(lambda: Decimal("0.00"))
    counts_by_category = defaultdict(int)
    counts_by_status = defaultdict(int)
    currency = "BRL"
    total_count = 0

    try:
        tree = ET.parse(attachment_path)
        root = tree.getroot()
        for tx in root.findall("Transaction"):
            total_count += 1

            # Amount + currency
            amount_el = tx.find("Amount")
            if amount_el is not None:
                currency = (amount_el.attrib.get("currency", "BRL") or "BRL").upper()
                amount_val = amount_el.text or "0"
                amount = _safe_decimal(amount_val)
            else:
                amount = Decimal("0.00")

            # Category (fallback to Type)
            cat = (tx.findtext("Category") or tx.findtext("Type") or "").strip().upper() or "UNKNOWN"
            totals_by_category[cat] += amount
            counts_by_category[cat] += 1

            # Status (lower-case for consistency)
            status = (tx.findtext("Status") or "").strip().lower() or "unknown"
            counts_by_status[status] += 1

    except Exception:
        # If parsing fails, return empty analytics to keep email flow
        pass

    return (
        dict(totals_by_category),
        dict(counts_by_category),
        dict(counts_by_status),
        currency,
        total_count,
    )

def _compose_email(month: str, metrics: dict, attachment_path: str):
    subject = f"Transactional Report — {month}"

    # --- Analytics (from XML) ---
    totals_by_cat, counts_by_cat, counts_by_status, currency, xml_count = _analytics_from_xml(attachment_path)

    analytics_lines = [f"Analytics — {month}", ""]
    analytics_lines.append("Totals by Category (BRL):")
    if totals_by_cat:
        for cat in sorted(totals_by_cat.keys()):
            analytics_lines.append(f"- {cat}: {totals_by_cat[cat]:.2f} {currency}")
    else:
        analytics_lines.append("- No transactions found in XML.")

    analytics_lines.append("")
    analytics_lines.append("Total Transactions by Category:")
    if counts_by_cat:
        for cat in sorted(counts_by_cat.keys()):
            analytics_lines.append(f"- {cat}: {counts_by_cat[cat]}")
    else:
        analytics_lines.append("- No transactions found in XML.")

    # Totals by status (approved & chargeback)
    analytics_lines.append("")
    analytics_lines.append("Total Transactions by Status:")
    approved_count = counts_by_status.get("approved", 0)
    chargeback_count = counts_by_status.get("chargeback", 0)
    analytics_lines.append(f"- approved: {approved_count}")
    analytics_lines.append(f"- chargeback: {chargeback_count}")

    # --- Summary (simple, as before) ---
    lines = [
        f"Month: {month}",
        f"Rows in: {metrics.get('rows_in', 0)}",
        f"Rows out: {metrics.get('rows_out', 0)}",
        f"Duplicates removed: {metrics.get('duplicates_removed', 0)}",
        f"Below-threshold excluded: {metrics.get('below_threshold_excluded', 0)}",
        f"Invalid labels: {metrics.get('invalid_labels', 0)}",
        f"Invalid dates: {metrics.get('invalid_dates', 0)}",
        f"Invalid amounts: {metrics.get('invalid_amounts', 0)}",
        f"Invalid currency: {metrics.get('invalid_currency', 0)}",
        f"Transactions in XML: {xml_count}",
    ]

    # Alerts (unchanged)
    alerts = []
    if metrics.get("duplicates_removed", 0) > 0:
        alerts.append("Duplicates were detected and removed.")
    if metrics.get("invalid_labels", 0) > 0:
        alerts.append("Some labels were invalid and normalized to defaults.")
    if metrics.get("invalid_dates", 0) > 0:
        alerts.append("Some rows had invalid dates and were excluded.")
    if metrics.get("below_threshold_excluded", 0) > 0:
        alerts.append("Some rows had non-positive amounts and were excluded.")
    if not alerts:
        alerts.append("No alerts.")

    body = (
        "\n".join(analytics_lines)
        + "\n\nSummary:\n" + "\n".join(lines)
        + "\n\nAlerts:\n" + "\n".join(f"- {a}" for a in alerts)
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", "noreply@example.com"))
    msg["To"] = os.getenv("EMAIL_TO", "ops@example.com")
    msg.set_content(body)

    # attach XML
    with open(attachment_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="xml",
            filename=os.path.basename(attachment_path),
        )
    return msg

def _smtp_settings_from_env():
    """
    Returns a tuple (host, port, user, password, use_tls, use_ssl).
    - Gmail recommended: smtp.gmail.com:587 with STARTTLS (use_tls=True), or 465 with SSL (use_ssl=True).
    """
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "0") or "0")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    provider = os.getenv("SMTP_PROVIDER", "").lower()

    if provider == "gmail":
        if not host:
            host = "smtp.gmail.com"
        if port == 0:
            port = 587  # STARTTLS default
    use_tls = os.getenv("SMTP_TLS", "true").lower() in ("1", "true", "yes")
    use_ssl = os.getenv("SMTP_SSL", "false").lower() in ("1", "true", "yes")
    if port == 465:
        use_ssl = True
        use_tls = False
    return host, port, user, password, use_tls, use_ssl

def send_report_email(month: str, metrics: dict, attachment_path: str, out_dir: str):
    msg = _compose_email(month, metrics, attachment_path)

    host, port, user, password, use_tls, use_ssl = _smtp_settings_from_env()

    # If SMTP not configured, write .eml as evidence
    if not host or port == 0:
        eml_path = os.path.join(out_dir, f"email_{month.replace('-','')}.eml")
        with open(eml_path, "wb") as f:
            f.write(msg.as_bytes())
        return {"status": "saved", "message": f"SMTP not configured; email saved to {eml_path}", "path": eml_path}

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                if use_tls:
                    server.starttls(context=context)
                    server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)

        # Always save evidence even on successful send
        sent_eml_path = os.path.join(out_dir, f"email_evidence_{month.replace('-','')}_SENT.eml")
        with open(sent_eml_path, "wb") as f:
            f.write(msg.as_bytes())

        return {"status": "sent", "message": f"Email sent to {msg['To']} (copy saved to {sent_eml_path})", "path": sent_eml_path}

    except smtplib.SMTPAuthenticationError as e:
        hint = "Authentication failed. For Gmail, enable 2-Step Verification and use an App Password."
        eml_path = os.path.join(out_dir, f"email_{month.replace('-','')}_AUTHFAILED.eml")
        with open(eml_path, "wb") as f:
            f.write(msg.as_bytes())
        return {"status": "failed", "message": f"{hint} Saved EML to {eml_path}. Error: {e}"}
    except Exception as e:
        eml_path = os.path.join(out_dir, f"email_{month.replace('-','')}_FAILED.eml")
        with open(eml_path, "wb") as f:
            f.write(msg.as_bytes())
        log_path = os.path.join(out_dir, f"email_error_{month.replace('-','')}.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("Error sending email:\n")
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
        return {"status": "failed", "message": f"Saved EML to {eml_path}; see {log_path} for details."}
from datetime import datetime
from decimal import Decimal, InvalidOperation

ALLOWED_STATUSES = {"approved", "chargeback", "reversed", "refunded", "pending", "declined"}
ALLOWED_TYPES = {"DEBIT", "CREDIT"}

def _parse_date_to_iso(date_str: str):
    """Try multiple formats and return date in YYYY-MM-DD format."""
    fmts = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S"
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    # Fallback: if looks like YYYY-MM-DD
    if isinstance(date_str, str) and len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str[:10]
    return None

def normalize_and_filter(rows, target_month: str):
    """Normalize transactions and filter by month, returning normalized rows and metrics."""
    seen_ids = set()
    normalized = []
    metrics = {
        "duplicates_removed": 0,
        "below_threshold_excluded": 0,
        "invalid_labels": 0,
        "invalid_dates": 0,
        "invalid_amounts": 0,
        "invalid_currency": 0
    }

    for r in rows:
        # --- Map different possible column headers ---
        tid = (
            r.get("id")
            or r.get("transaction_id")
            or r.get("transaction_code")
            or ""
        ).strip()
        if not tid:
            continue

        # Deduplication
        if tid in seen_ids:
            metrics["duplicates_removed"] += 1
            continue
        seen_ids.add(tid)

        # Status
        status_raw = (r.get("status") or "").strip().lower()
        status = status_raw if status_raw in ALLOWED_STATUSES else "unknown"
        if status == "unknown":
            metrics["invalid_labels"] += 1

        # Date
        date_iso = _parse_date_to_iso(
            (r.get("date") or r.get("timestamp") or "").strip()
        )
        if not date_iso:
            metrics["invalid_dates"] += 1
            continue

        # Keep only rows from the target month
        if not date_iso.startswith(target_month):
            continue

        # Amount
        currency = (r.get("currency") or "BRL").strip().upper()
        if not currency:
            metrics["invalid_currency"] += 1
            currency = "BRL"
        amt_raw = r.get("amount") or r.get("amount_BRL") or "0"
        amt_raw = str(amt_raw).replace(",", ".")  # normalize comma to dot
        try:
            amt = Decimal(amt_raw).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            metrics["invalid_amounts"] += 1
            continue
        if amt <= Decimal("0.00"):
            metrics["below_threshold_excluded"] += 1
            continue

        # Type
        type_raw = (r.get("type") or r.get("category") or "").strip().upper()
        ttype = type_raw if type_raw in ALLOWED_TYPES else "DEBIT"
        if ttype not in ALLOWED_TYPES:
            metrics["invalid_labels"] += 1

        # MerchantId
        merchant_id = (
            r.get("merchant_id")
            or r.get("merchant")
            or ""
        )
        merchant_id = merchant_id.replace(".", "").replace("/", "").replace("-", "").strip()

        # Network
        network = str(r.get("network") or "1").strip()
        try:
            network_int = int(network)
        except Exception:
            network_int = 1

        # Category
        category = (r.get("category") or ttype).strip().upper()

        normalized.append({
            "id": tid,
            "Status": status,
            "Date": date_iso,
            "Amount": f"{amt:.2f}",
            "Currency": currency,
            "Type": ttype,
            "MerchantId": merchant_id,
            "Network": str(network_int),
            "Category": category
        })

    return normalized, metrics
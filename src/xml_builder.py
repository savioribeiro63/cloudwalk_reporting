import xml.etree.ElementTree as ET
from datetime import datetime, timezone

def build_xml_report(month: str, rows, out_path: str):
    root = ET.Element("TransactionsReport", attrib={
        "month": month,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    })
    for r in rows:
        tx = ET.SubElement(root, "Transaction", attrib={"id": r["id"]})
        s = ET.SubElement(tx, "Status")
        s.text = r["Status"]
        d = ET.SubElement(tx, "Date")
        d.text = r["Date"]
        amt = ET.SubElement(tx, "Amount", attrib={"currency": r["Currency"]})
        amt.text = r["Amount"]
        t = ET.SubElement(tx, "Type")
        t.text = r["Type"]
        m = ET.SubElement(tx, "MerchantId")
        m.text = r["MerchantId"]
        n = ET.SubElement(tx, "Network")
        n.text = r["Network"]
        c = ET.SubElement(tx, "Category")
        c.text = r["Category"]

    tree = ET.ElementTree(root)
    # Ensure pretty print with indentation (Python 3.9+ has ET.indent)
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path

# Local Reporting Mini-System (Python)

## Objective
Transform a CSV of transactions into a normalized **single XML report** per month and send a concise email summary with alerts. Runs **entirely local** via CLI or a **local REST endpoint**.

---

## Project Structure
```
.
├── app.py
├── requirements.txt
├── .env.example
├── data/
│   └── transactions.csv           # sample test data
├── outputs/
│   └── <YYYYMM>/report.xml        # generated
│       <YYYYMM>/summary.json      # generated (optional)
│       <YYYYMM>/email_*.eml       # evidence of email sending
└── src/
    ├── __init__.py
    ├── api.py                     # Flask REST endpoint: POST /run
    ├── processing.py              # Orchestrates the pipeline
    ├── reader.py                  # CSV reader
    ├── normalizer.py              # Normalization + filtering rules
    ├── xml_builder.py             # XML generator
    ├── summary.py                 # Metrics builder + writer
    └── emailer.py                 # SMTP/email (.eml fallback)
```

---

## Installation

### 1. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate
```

### 2. Install requirements
We simplified dependencies to avoid pandas build issues on macOS ARM. The system only requires:
- Flask (for REST API)
- python-dotenv (to read `.env`)

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Contents of `requirements.txt`:
```text
Flask>=3.0,<4.0
python-dotenv>=1.0,<2.0
```

### 3. Configure environment variables
```bash
cp .env.example .env
# edit .env with your SMTP or Gmail app password
```

---

## CLI Usage
```bash
python app.py --month=YYYY-MM --input=./data/transactions.csv --output=./outputs --send-email
```
- `--send-email` is optional. If SMTP is not configured, an `.eml` file is created as **evidence**.

### Example
```bash
python app.py --month=2023-08 --input=./data/transactions.csv --output=./outputs --send-email
```

---

## Local REST Endpoint (Implemented Option)
Start the API:
```bash
python app.py --api --host=127.0.0.1 --port=8000 --output=./outputs --input=./data/transactions.csv
```

Health check:
```bash
curl  
```

Trigger a run:
```bash
curl -X POST http://127.0.0.1:8000/run \\
  -H "Content-Type: application/json" \\
  -d '{"month":"2023-08","send_email":true}'
```

**Response** (example):
```json
{
  "id": "3a8f9f6f-9f9c-4b7e-8d1d-6f63b3271c48",
  "status": "completed",
  "report_path": "outputs/202308/report.xml",
  "summary_path": "outputs/202308/summary.json",
  "metrics": { ... },
  "email": {
    "status": "saved",
    "message": "SMTP not configured; email saved to outputs/202308/email_202308.eml"
  }
}
```

---

## Normalization & Filtering Rules
- **Accepted input columns**:  
  - `transaction_code` (→ internal `id`)  
  - `timestamp` (→ internal `date`)  
  - `amount_BRL` (→ internal `amount`, currency fixed as BRL)  
  - `status` (→ normalized lowercase)  
  - `category` (→ normalized uppercase, used for grouping)  
  - `merchant_id`, `network`  
- **Dates** parsed and normalized to `YYYY-MM-DD` (supports `YYYY-MM-DD HH:MM:SS`, `dd-MM-YYYY`, etc.).  
- **Filter by month**: only rows where the normalized `date` starts with the requested `YYYY-MM`.  
- **Amount** must be `> 0.00` (non-positive rows are excluded).  
- **Currency** always set to `BRL` (uppercased).  
- **Status** normalized to lowercase; allowed `{approved, chargeback, reversed, refunded, pending, declined}`. Unknown → `unknown` (counted in `invalid_labels`).  
- **Type/Category** uppercased; allowed `{DEBIT, CREDIT}`. Unknown → `DEBIT` by default (counted in `invalid_labels`).  
- **Deduplication**: transactions with the same `transaction_code` → only first occurrence kept.  
- **MerchantId** normalized (punctuation removed).  
- **Network** parsed as integer; defaults to `1`.  
- **Category** is preserved from input (or defaults to `Type`).  

### Email Analytics
Every run also computes aggregated analytics (from the generated XML):  
- **Totals by Category (BRL)**: sum of amounts for each category (DEBIT, CREDIT).  
- **Total Transactions by Category**: count of transactions grouped by category.  
- **Total Transactions by Status**: counts for `approved` and `chargeback`.  

Rules can be customized in `src/normalizer.py`, and email analytics can be adjusted in `src/emailer.py`.

---

## Email
- Subject: `Transactional Report — YYYY-MM`
- Body: concise **technical summary** and **alerts**
- Attachment: `report.xml`
- **Transport**: SMTP if `.env` configured; otherwise `.eml` is written.

Configure `.env`:
```ini
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
SMTP_TLS=true
EMAIL_FROM=reports@example.com
EMAIL_TO=alerts@example.com
```

---

## Gmail SMTP
To send the email via Gmail:

1. In your Google Account, enable **2-Step Verification**.  
2. Create an **App Password** (Security → App passwords → choose “Mail” + your device).  
3. Edit `.env` like this:
   ```ini
   SMTP_PROVIDER=gmail
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_TLS=true
   SMTP_SSL=false
   SMTP_USER=your_gmail_address@gmail.com
   SMTP_PASS=your_16_char_app_password
   EMAIL_FROM=your_gmail_address@gmail.com
   EMAIL_TO=alerts@example.com
   ```
4. Run with `--send-email`.  
   If delivery fails, the system saves a `.eml` file in `outputs/<YYYYMM>/` and logs the error.

---

## Decisions & Notes
- Chosen interface: **Local REST endpoint** (Flask).
- Simplified `requirements.txt` (removed pandas) for easier cross-platform install.
- `.eml` fallback ensures evidence even without SMTP.
- XML matches Appendix A structure.
- Metrics written to `summary.json`.

---

## Key AI Prompts Used (abridged)
1. *"Help me design a local Python system that reads a transactions CSV, normalizes data, outputs a single XML per month, and emails a summary with alerts. Provide a clean module structure, CLI + REST endpoint, and a README."*
2. *"Write a normalization function for transactions (date to ISO, dedup by id, positive amounts only, allowed status/type, default currency BRL)."*
3. *"Generate a minimal, dependency-light email sender that uses SMTP from env and falls back to writing an .eml."*
4. *"Compose a concise email body summarizing metrics and alerts suitable for ops."*
5. *"Fix api.py decorators and indent to work in Flask."*
6. *"Simplify requirements.txt (remove pandas) to avoid build issues on macOS ARM."*

---

## Appendix
XML root:  
```xml
<TransactionsReport month="YYYY-MM" generated_at="...Z">
  <Transaction id="...">
    <Status>...</Status>
    <Date>...</Date>
    <Amount currency="BRL">...</Amount>
    <Type>...</Type>
    <MerchantId>...</MerchantId>
    <Network>...</Network>
    <Category>...</Category>
  </Transaction>
  ...
</TransactionsReport>
```

---

🚀 **Tip for macOS/zsh**:  
Use quotes around paths with spaces, e.g.:
```bash
cd "/Users/savioribeiro/Documents/local_reporting_mini_system 2"
```
and always run inside the venv:
```bash
source .venv/bin/activate
```

#!/usr/bin/env python3
import argparse
import os
import sys
from dotenv import load_dotenv
from src.processing import process_month
from src.api import create_app

# Load .env file and override any existing environment variables
load_dotenv(override=True)

def main():
    parser = argparse.ArgumentParser(description="Local Reporting Mini-System")
    parser.add_argument("--month", type=str, help="Target month in YYYY-MM format", required=False)
    parser.add_argument("--input", type=str, help="Path to transactions.csv", required=False, default="./data/transactions.csv")
    parser.add_argument("--output", type=str, help="Base output directory", required=False, default="./outputs")
    parser.add_argument("--send-email", action="store_true", help="Send email with summary and XML attachment")
    parser.add_argument("--api", action="store_true", help="Run local REST API instead of CLI processing")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.api:
        app = create_app(base_output=args.output, default_input=args.input)
        app.run(host=args.host, port=args.port, debug=False)
        return

    if not args.month:
        print("Error: --month is required in CLI mode.", file=sys.stderr)
        sys.exit(2)

    result = process_month(
        month=args.month,
        input_path=args.input,
        output_base=args.output,
        send_email=args.send_email,
    )

    print("Status:", result.get("status"))
    print("Report XML:", result.get("report_path"))
    if result.get("summary_path"):
        print("Summary JSON:", result.get("summary_path"))
    if result.get("email_result"):
        print(
            "Email:",
            result["email_result"]["status"],
            "-",
            result["email_result"].get("message", ""),
        )

if __name__ == "__main__":
    main()
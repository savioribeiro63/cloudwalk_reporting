from flask import Flask, request, jsonify
import uuid
from .processing import process_month

def create_app(base_output: str = "./outputs", default_input: str = "./data/transactions.csv"):
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/run", methods=["POST"])
    def run():
        payload = request.get_json(force=True, silent=True) or {}
        month = payload.get("month")
        input_path = payload.get("input", default_input)
        send_email = bool(payload.get("send_email", False))

        if not month or not isinstance(month, str) or len(month) != 7 or month[4] != "-":
            return jsonify({"error": "month must be 'YYYY-MM'"}), 400

        run_id = str(uuid.uuid4())
        result = process_month(
            month=month,
            input_path=input_path,
            output_base=base_output,
            send_email=send_email
        )
        status = "completed" if result.get("status") == "ok" else "failed"

        return jsonify({
            "id": run_id,
            "status": status,
            "report_path": result.get("report_path"),
            "summary_path": result.get("summary_path"),
            "metrics": result.get("metrics", {}),
            "email": result.get("email_result", {})
        }), 200 if status == "completed" else 500

    return app
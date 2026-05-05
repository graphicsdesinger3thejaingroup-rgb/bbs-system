"""
Bar Bending Schedule (BBS) Automation — Flask backend.

Endpoints:
  GET  /                 -> serves frontend (index.html)
  POST /calculate        -> validates + computes BBS
  POST /download-excel   -> returns generated .xlsx
  POST /download-pdf     -> returns generated .pdf
  GET  /health           -> health check
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import traceback

from services.validator import validate_payload
from services.calculator import build_bbs
from services.excel_generator import generate_excel
from services.pdf_generator import generate_pdf
from utils.logger import setup_logger


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# On Vercel / serverless: /tmp is the only writable location.
# Locally: keep using backend/generated/ so files stay near the project.
_IS_SERVERLESS = bool(os.environ.get("VERCEL") or
                      os.environ.get("VERCEL_ENV") or
                      os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
GEN_DIR = "/tmp/bbs_generated" if _IS_SERVERLESS \
          else os.path.join(BASE_DIR, "generated")
LOG_DIR = "/tmp/bbs_logs" if _IS_SERVERLESS \
          else os.path.join(BASE_DIR, "logs")

FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

logger = setup_logger("bbs_app", LOG_DIR)

app = Flask(__name__, static_folder=None)
CORS(app)


# ----------------- Frontend serving -----------------

@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>", methods=["GET"])
def static_files(filename):
    full = os.path.join(FRONTEND_DIR, filename)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"error": "Not found"}), 404


# ----------------- Health -----------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "bbs_app"})


# ----------------- Calculate -----------------

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        logger.info("calculate() payload received: %s", payload)

        ok, errs, warns = validate_payload(payload)
        if not ok:
            logger.warning("Validation failed: %s", errs)
            return jsonify({"success": False, "errors": errs, "warnings": warns}), 400

        result = build_bbs(payload)

        # Attach warnings into the result
        result["warnings"] = warns

        # Hard fail if internal double-check disagrees with stored values
        if not result["verification"]["passed"]:
            logger.error("Double-check failed: %s", result["verification"]["issues"])
            return jsonify({
                "success": False,
                "errors": ["Calculation mismatch detected — please recheck inputs."],
                "verification": result["verification"],
                "warnings": warns,
            }), 500

        logger.info("Calculation done. Total weight (with wastage): %s kg | warnings=%d",
                    result["summary"]["total_weight_kg_with_wastage"], len(warns))
        return jsonify({"success": True, "data": result})

    except ValueError as ve:
        logger.error("ValueError: %s", ve)
        return jsonify({"success": False, "errors": [str(ve)]}), 400
    except Exception as e:
        logger.exception("Unexpected error in /calculate")
        return jsonify({"success": False,
                        "errors": [f"Server error: {e}"]}), 500


# ----------------- Excel -----------------

@app.route("/download-excel", methods=["POST"])
def download_excel():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        ok, errs, _warns = validate_payload(payload)
        if not ok:
            return jsonify({"success": False, "errors": errs}), 400

        result = build_bbs(payload)
        if not result["verification"]["passed"]:
            return jsonify({"success": False,
                            "errors": ["Calculation mismatch — refusing to export."],
                            "verification": result["verification"]}), 500

        path = generate_excel(result, GEN_DIR,
                              project_name=payload.get("project_name", "BBS_Report"))
        logger.info("Excel generated: %s", path)
        return send_file(path, as_attachment=True,
                         download_name=os.path.basename(path),
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        logger.exception("Error in /download-excel")
        return jsonify({"success": False, "errors": [str(e)]}), 500


# ----------------- PDF -----------------

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        ok, errs, _warns = validate_payload(payload)
        if not ok:
            return jsonify({"success": False, "errors": errs}), 400

        result = build_bbs(payload)
        if not result["verification"]["passed"]:
            return jsonify({"success": False,
                            "errors": ["Calculation mismatch — refusing to export."],
                            "verification": result["verification"]}), 500

        path = generate_pdf(
            result, GEN_DIR,
            project_name=payload.get("project_name") or "BBS_Report",
            client_name =payload.get("client_name"),
            company_name=payload.get("company_name"),
            logo_path   =payload.get("logo_path"),
        )
        logger.info("PDF generated: %s", path)
        return send_file(path, as_attachment=True,
                         download_name=os.path.basename(path),
                         mimetype="application/pdf")
    except Exception as e:
        logger.exception("Error in /download-pdf")
        return jsonify({"success": False, "errors": [str(e)]}), 500


# ----------------- Error handlers -----------------

@app.errorhandler(404)
def _404(e):
    return jsonify({"error": "Not Found"}), 404


@app.errorhandler(500)
def _500(e):
    logger.error("500 error: %s\n%s", e, traceback.format_exc())
    return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    logger.info("Starting BBS app on :%d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)

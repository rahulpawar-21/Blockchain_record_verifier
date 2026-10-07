from functools import wraps
from io import BytesIO
from pathlib import Path

import qrcode
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, send_file

from blockchain import Blockchain
from database import Database

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = "recordchain-development-secret-change-me"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

blockchain = Blockchain(str(BASE_DIR / "data" / "blockchain.json"))
database = Database(str(BASE_DIR / "data" / "records.db"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/")
def index():
    return redirect(url_for("dashboard" if session.get("admin_logged_in") else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if database.authenticate(username, password):
            session.clear()
            session["admin_logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    valid, errors = blockchain.validate()
    return render_template("dashboard.html", records=database.list_records(), chain=blockchain.to_list(), valid=valid, errors=errors, username=session.get("username"))


@app.get("/blockchain")
@login_required
def blockchain_page():
    valid, errors = blockchain.validate()
    return render_template("blockchain.html", chain=blockchain.to_list(), valid=valid, errors=errors)


@app.get("/verify")
def verify_page():
    return render_template("verify.html")


@app.get("/api/health")
def api_health():
    valid, errors = blockchain.validate()
    return jsonify({"status": "ok", "blockchain_valid": valid, "blocks": len(blockchain.chain), "errors": errors})


@app.get("/api/chain")
def api_chain():
    valid, errors = blockchain.validate()
    return jsonify({"valid": valid, "errors": errors, "chain": blockchain.to_list()})


@app.get("/api/records")
def api_records():
    return jsonify(database.list_records())


@app.post("/api/records")
@login_required
def api_add_record():
    data = request.get_json(silent=True) or {}
    required = ["certificate_id", "student_name", "srn", "course", "subject", "marks"]
    missing = [key for key in required if data.get(key) in (None, "")]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        marks = int(data["marks"])
    except (TypeError, ValueError):
        return jsonify({"error": "Marks must be an integer."}), 400
    if not 0 <= marks <= 100:
        return jsonify({"error": "Marks must be between 0 and 100."}), 400

    record = {
        "type": "MARKS_RECORD",
        "certificate_id": str(data["certificate_id"]).strip(),
        "student_name": str(data["student_name"]).strip(),
        "srn": str(data["srn"]).strip(),
        "course": str(data["course"]).strip(),
        "subject": str(data["subject"]).strip(),
        "marks": marks,
    }
    if database.get_record(record["certificate_id"]):
        return jsonify({"error": "Certificate ID already exists."}), 409

    chain_valid, _ = blockchain.validate()
    if not chain_valid:
        return jsonify({"error": "Blockchain is currently invalid. Reset the demo before adding records."}), 409

    block = blockchain.add_record(record)
    record_row = {**record, "original_marks": marks, "block_index": block.index, "created_at": block.timestamp}
    try:
        database.add_record(record_row)
    except Exception as exc:
        blockchain.chain.pop(); blockchain.save()
        return jsonify({"error": f"Could not save record: {exc}"}), 409
    return jsonify({"success": True, "block": block.to_dict()}), 201


@app.post("/api/records/<certificate_id>/correct")
@login_required
def api_correct_record(certificate_id):
    existing = database.get_record(certificate_id)
    if not existing:
        return jsonify({"error": "Certificate not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        new_marks = int(data.get("marks"))
    except (TypeError, ValueError):
        return jsonify({"error": "Marks must be an integer."}), 400
    if not 0 <= new_marks <= 100:
        return jsonify({"error": "Marks must be between 0 and 100."}), 400
    chain_valid, _ = blockchain.validate()
    if not chain_valid:
        return jsonify({"error": "Blockchain is currently invalid. Reset the demo before recording a correction."}), 409
    if new_marks == existing["marks"]:
        return jsonify({"error": "Correction must change the marks value."}), 400

    reason = str(data.get("reason", "Official correction")).strip()[:200] or "Official correction"
    record = {
        "type": "MARKS_CORRECTION",
        "certificate_id": certificate_id,
        "student_name": existing["student_name"],
        "srn": existing["srn"],
        "course": existing["course"],
        "subject": existing["subject"],
        "previous_marks": existing["marks"],
        "marks": new_marks,
        "reason": reason,
    }
    block = blockchain.add_record(record)
    try:
        database.add_correction({
            "certificate_id": certificate_id,
            "previous_marks": existing["marks"],
            "new_marks": new_marks,
            "reason": reason,
            "block_index": block.index,
            "created_at": block.timestamp,
        })
        database.update_marks(certificate_id, new_marks)
    except Exception as exc:
        blockchain.chain.pop(); blockchain.save()
        return jsonify({"error": f"Could not save correction: {exc}"}), 409
    return jsonify({"success": True, "message": "Correction recorded as a new block. Historical block was not edited.", "block": block.to_dict()}), 201


@app.get("/api/records/<certificate_id>")
def api_verify(certificate_id):
    record = database.get_record(certificate_id)
    valid, errors = blockchain.validate()
    if not record:
        return jsonify({"verified": False, "error": "Certificate not found", "blockchain_valid": valid}), 404
    block_index = record["block_index"]
    block = next((b for b in blockchain.chain if b.index == block_index), None)
    if block is None:
        return jsonify({"verified": False, "error": "Associated blockchain block not found", "blockchain_valid": valid}), 404
    calculated = block.calculate_hash()
    record_hash_valid = calculated == block.hash
    verified = valid and record_hash_valid and block.record.get("certificate_id") == certificate_id
    corrections = database.list_corrections(certificate_id)
    return jsonify({"verified": verified, "record": record, "block": block.to_dict(), "corrections": corrections, "blockchain_valid": valid, "record_hash_valid": record_hash_valid, "errors": errors})


@app.get("/verify/qr/<certificate_id>")
def certificate_qr(certificate_id):
    if not database.get_record(certificate_id):
        return jsonify({"error": "Certificate not found"}), 404
    verify_url = request.url_root.rstrip("/") + url_for("verify_page") + "?certificate=" + certificate_id
    image = qrcode.make(verify_url)
    output = BytesIO(); image.save(output, format="PNG"); output.seek(0)
    return send_file(output, mimetype="image/png", download_name=f"{certificate_id}.png")


@app.post("/api/tamper")
@login_required
def api_tamper():
    data = request.get_json(silent=True) or {}
    try:
        block_index = int(data.get("block_index"))
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return jsonify({"error": "Block index and marks must be integers."}), 400
    try:
        block = blockchain.tamper(block_index, "marks", value)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    valid, errors = blockchain.validate()
    return jsonify({"success": True, "valid": valid, "errors": errors, "tampered_block": block.to_dict()})


@app.post("/api/reset-demo")
@login_required
def api_reset_demo():
    # Rebuild from trusted application data, not from the potentially tampered chain.
    fresh = Blockchain(str(BASE_DIR / "data" / "blockchain_demo_reset.json"))
    fresh.chain = [fresh.create_genesis_block()]
    records = sorted(database.list_records(), key=lambda row: row["id"])
    for row in records:
        fresh.add_record({"type": "MARKS_RECORD", "certificate_id": row["certificate_id"], "student_name": row["student_name"], "srn": row["srn"], "course": row["course"], "subject": row["subject"], "marks": row["original_marks"]})
        for correction in database.list_corrections(row["certificate_id"]):
            fresh.add_record({"type": "MARKS_CORRECTION", "certificate_id": row["certificate_id"], "student_name": row["student_name"], "srn": row["srn"], "course": row["course"], "subject": row["subject"], "previous_marks": correction["previous_marks"], "marks": correction["new_marks"], "reason": correction["reason"]})
    blockchain.chain = fresh.chain
    blockchain.save()
    valid, errors = blockchain.validate()
    return jsonify({"success": True, "valid": valid, "errors": errors})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)

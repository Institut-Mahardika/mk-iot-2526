# app.py
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from db import init_mysql, get_conn
import os

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/")

# Konfigurasi DB dari ENV (tetap sama key-nya agar kompatibel dengan .env kamu)
app.config.update(
    DB_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
    DB_PORT=int(os.getenv("MYSQL_PORT", 3306)),
    DB_NAME=os.getenv("MYSQL_DB", "iot_scan"),
    DB_USER=os.getenv("MYSQL_USER", "root"),
    DB_PASS=os.getenv("MYSQL_PASSWORD", "ServBay.dev"),
    DB_POOL_SIZE=int(os.getenv("DB_POOL_SIZE", "5")),
)

# init pool
init_mysql(app)

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

# ---------------- API INSERT ----------------
@app.post("/api/ldr/insert")
def insert_ldr():
    """
    Body JSON:
    {
      "device_id": "esp32-001",
      "angle_deg": 0..180,
      "ldr_state": 0|1,
      "raw_value": 0..4095 (opsional)
    }
    """
    data = request.get_json(silent=True) or {}
    try:
        device_id = data.get("device_id", "esp32-001")
        angle_deg = int(data["angle_deg"])
        ldr_state = int(data["ldr_state"])
        raw_value = data.get("raw_value")
        if raw_value is not None:
            raw_value = int(raw_value)

        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "INSERT INTO ldr_readings(device_id, angle_deg, ldr_state, raw_value) "
                "VALUES (%s,%s,%s,%s)",
                (device_id, angle_deg, ldr_state, raw_value),
            )
            conn.commit()
            cur.close()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 400

# --------------- API QUERY DATA -------------
@app.get("/api/ldr/latest")
def latest():
    n = int(request.args.get("n", 180))
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT angle_deg, ldr_state, raw_value, created_at "
            "FROM ldr_readings ORDER BY id DESC LIMIT %s", (n,)
        )
        rows = cur.fetchall()
        cur.close()
    return jsonify(rows), 200

# --------------- API SETTINGS ---------------
@app.get("/api/settings")
def get_settings():
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM settings WHERE id=1")
        row = cur.fetchone()
        cur.close()
    return jsonify(row), 200

@app.post("/api/settings")
def update_settings():
    data = request.get_json(silent=True) or request.form
    fields, params = [], []
    for k in ("yellow_logic", "red_hold_ms", "servo_mode", "servo_target"):
        if k in data:
            fields.append(f"{k}=%s")
            params.append(data[k])
    if not fields:
        return jsonify({"ok": False, "message": "no changes"}), 400

    params.append(1)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE settings SET {', '.join(fields)} WHERE id=%s", params)
        conn.commit()
        cur.close()
    return jsonify({"ok": True}), 200

# -------------- API COMMAND DEVICE ----------
@app.get("/api/servo/target")
def servo_target():
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT servo_mode, servo_target FROM settings WHERE id=1")
        s = cur.fetchone()
        cur.close()
    target = -1 if s["servo_mode"] == "auto" else int(s["servo_target"])
    return jsonify({"target": target}), 200
  
# ------------- API EXPORT CSV -------------
@app.get("/api/ldr/export.csv")
def export_csv():
    from io import StringIO
    import csv
    # gunakan helper pool yang sudah ada
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id,device_id,angle_deg,ldr_state,raw_value,created_at "
            "FROM ldr_readings ORDER BY id DESC LIMIT 2000"
        )
        rows = cur.fetchall()
        cur.close()

    si = StringIO()
    w = csv.writer(si)
    w.writerow(["id","device_id","angle_deg","ldr_state","raw_value","created_at"])
    for r in rows:
        w.writerow([r["id"], r["device_id"], r["angle_deg"], r["ldr_state"], r["raw_value"] or "", r["created_at"]])

    return (si.getvalue(), 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=ldr_readings.csv"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100, debug=True)
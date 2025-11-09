from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from db import mysql, init_mysql
import os

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/")

# Ambil ENV → masukkan ke config
app.config.update(
    MYSQL_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
    MYSQL_PORT=int(os.getenv("MYSQL_PORT", 3306)),
    MYSQL_DB=os.getenv("MYSQL_DB", "iot_scan"),           # alias
    MYSQL_DATABASE=os.getenv("MYSQL_DB", "iot_scan"),     # nama yang dibaca lib
    MYSQL_USER=os.getenv("MYSQL_USER", "root"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", "ServBay.dev"),
)
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

        conn = mysql.connection           # dari flask-mysql-connector
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
    conn = mysql.connection
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
    conn = mysql.connection
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
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(f"UPDATE settings SET {', '.join(fields)} WHERE id=%s", params)
    conn.commit()
    cur.close()
    return jsonify({"ok": True}), 200

# -------------- API COMMAND DEVICE ----------
@app.get("/api/servo/target")
def servo_target():
    conn = mysql.connection
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT servo_mode, servo_target FROM settings WHERE id=1")
    s = cur.fetchone()
    cur.close()
    target = -1 if s["servo_mode"] == "auto" else int(s["servo_target"])
    return jsonify({"target": target}), 200

if __name__ == "__main__":
    # Jalankan dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
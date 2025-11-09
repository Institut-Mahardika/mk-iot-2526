from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from db import init_mysql, get_conn
import os

load_dotenv()
app = Flask(__name__, static_folder="static", static_url_path="/")

# Koneksi DB
app.config.update(
    MYSQL_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
    MYSQL_PORT=int(os.getenv("MYSQL_PORT", 3306)),
    MYSQL_DB=os.getenv("MYSQL_DB", "iot_scan"),
    MYSQL_USER=os.getenv("MYSQL_USER", "root"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", "ServBay.dev"),
    MYSQL_POOL_SIZE=int(os.getenv("MYSQL_POOL_SIZE", 5)),
)
init_mysql(app)

@app.get("/")
def home():
    # layani frontend
    return send_from_directory("static", "index.html")

# === API: insert pembacaan dari ESP32 (LDR + servo angle) ===
@app.post("/api/ldr/insert")
def insert_ldr():
    """
    JSON yang diterima: {
      "device_id": "esp32-001",
      "angle_deg": 0..180,
      "ldr_state": 0|1,     # 1 = gelap, 0 = terang
      "raw_value": 0..4095  # opsional
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

        conn = get_conn(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO ldr_readings(device_id, angle_deg, ldr_state, raw_value) VALUES (%s,%s,%s,%s)",
            (device_id, angle_deg, ldr_state, raw_value),
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 400

# === API: query data untuk grafik radar ===
@app.get("/api/ldr/latest")
def latest():
    """Ambil N terbaru (default 180) untuk ditampilkan sebagai polar/radar."""
    n = int(request.args.get("n", 180))
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT angle_deg, ldr_state, raw_value, created_at "
        "FROM ldr_readings ORDER BY id DESC LIMIT %s", (n,)
    )
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify(rows), 200

# === API: settings (baca & ubah dari UI) ===
@app.get("/api/settings")
def get_settings():
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM settings WHERE id=1")
    row = cur.fetchone(); cur.close(); conn.close()
    return jsonify(row), 200

@app.post("/api/settings")
def update_settings():
    data = request.get_json(silent=True) or request.form
    fields = []
    params = []
    for key in ("yellow_logic", "red_hold_ms", "servo_mode", "servo_target"):
        if key in data:
            fields.append(f"{key}=%s")
            params.append(data[key])
    if not fields:
        return jsonify({"ok": False, "message": "no changes"}), 400

    params.append(1)
    conn = get_conn(); cur = conn.cursor()
    cur.execute(f"UPDATE settings SET {', '.join(fields)} WHERE id=%s", params)
    conn.commit(); cur.close(); conn.close()
    return jsonify({"ok": True}), 200

# === API: perintah langsung ke device (poling dari ESP32) ===
@app.get("/api/servo/target")
def servo_target():
    """Dipanggil ESP32: jika mode manual, kirim target derajat; jika auto, kirim -1."""
    conn = get_conn(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT servo_mode, servo_target FROM settings WHERE id=1")
    s = cur.fetchone(); cur.close(); conn.close()
    target = -1 if s["servo_mode"] == "auto" else int(s["servo_target"])
    return jsonify({"target": target}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from db import init_mysql, get_conn
import os
load_dotenv()

app = Flask(__name__)
app.config.update(
    MYSQL_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
    MYSQL_PORT=int(os.getenv("MYSQL_PORT", 3306)),
    MYSQL_DB=os.getenv("MYSQL_DB", "iot_db"),
    MYSQL_USER=os.getenv("MYSQL_USER", "root"),
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", "ServBay.dev"),
    MYSQL_POOL_SIZE=int(os.getenv("MYSQL_POOL_SIZE", 5)),
)
init_mysql(app)

@app.get("/")
def index():
    return "IoT Flask API (Ultrasonic) aktif 🚀"

@app.post("/ultrasonic/insert")
def insert_ultrasonic():
    """
    Terima:
    JSON: {"distance_cm": 12.3, "threshold_cm": 15, "triggered": true, "device_id":"esp32-001"}
    atau Form: distance_cm=...&threshold_cm=...&triggered=true&device_id=...
    """
    try:
        data = request.get_json(silent=True) or request.form

        if "distance_cm" not in data:
            return jsonify({"ok": False, "message": "distance_cm wajib ada"}), 400

        distance_cm = float(data.get("distance_cm"))
        threshold_cm = float(data.get("threshold_cm", 15))
        # triggered opsional; jika tak dikirim, hitung otomatis: true bila distance <= threshold
        triggered_raw = data.get("triggered")
        if triggered_raw is None:
            triggered = distance_cm <= threshold_cm
        else:
            triggered = str(triggered_raw).lower() in ("1", "true", "yes", "on")

        device_id = data.get("device_id", "esp32-001")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO iot_ultrasonic (distance_cm, threshold_cm, triggered, device_id)
            VALUES (%s, %s, %s, %s)
            """,
            (distance_cm, threshold_cm, int(triggered), device_id),
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "ok": True,
            "device_id": device_id,
            "distance_cm": distance_cm,
            "threshold_cm": threshold_cm,
            "triggered": triggered
        }), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"ok": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
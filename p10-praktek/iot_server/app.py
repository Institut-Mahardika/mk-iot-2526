# app.py
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from db import init_mysql, get_conn
import os
import requests
import time
import math
import io
from typing import List, Dict, Any

import matplotlib
matplotlib.use("Agg")        # backend non-GUI untuk generate PNG
import matplotlib.pyplot as plt

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/")

# --- Load configuration from environment ---
def load_config(app: Flask) -> None:
    # Konfigurasi DB dari ENV (tetap sama key-nya agar kompatibel dengan .env kamu)
    app.config.update(
        DB_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
        DB_PORT=int(os.getenv("MYSQL_PORT", 3306)),
        DB_NAME=os.getenv("MYSQL_DB", "iot_scan"),
        DB_USER=os.getenv("MYSQL_USER", "root"),
        DB_PASS=os.getenv("MYSQL_PASSWORD", "ServBay.dev"),
        DB_POOL_SIZE=int(os.getenv("DB_POOL_SIZE", "5")),
    )

load_config(app)

# --- Telegram config ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Cooldown supaya bot tidak spam
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "30"))
LAST_ALERT_TS = 0.0   # di-update saat kirim alert merah

def send_telegram(text: str) -> None:
    """Kirim pesan sederhana ke Telegram. Silent kalau belum di-set."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] not configured, skip send")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=5,
        )
        if not r.ok:
            print("[telegram] send failed:", r.status_code, r.text)
    except Exception as e:
        print("[telegram] error:", e)

def send_radar_snapshot() -> None:
    """Ambil data terakhir, render radar sederhana, kirim ke Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] not configured, skip radar snapshot")
        return

    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT angle_deg, ldr_state "
                "FROM ldr_readings ORDER BY id DESC LIMIT 180"
            )
            rows: List[Dict[str, Any]] = cur.fetchall()
        finally:
            cur.close()

    if not rows:
        send_telegram("Radar snapshot gagal: belum ada data.")
        return

    # urutkan berdasarkan sudut
    rows = sorted(rows, key=lambda r: r["angle_deg"])

    angles_deg = [r["angle_deg"] for r in rows]
    angles_rad = [a * math.pi / 180.0 for a in angles_deg]
    radius = [1.0 if r["ldr_state"] == 1 else 0.6 for r in rows]
    colors = ["#ff5757" if r["ldr_state"] == 1 else "#00ff99" for r in rows]

    fig = plt.figure(figsize=(4, 4))
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.scatter(angles_rad, radius, c=colors, s=22)
    ax.set_title("LDR Radar Snapshot", pad=16)
    ax.grid(alpha=0.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {"photo": ("radar.png", buf, "image/png")}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": "📡 Radar snapshot terbaru"}
    try:
        r = requests.post(url, data=data, files=files, timeout=10)
        if not r.ok:
            print("[telegram] send_radar_snapshot failed:", r.status_code, r.text)
    except Exception as e:
        print("[telegram] send_radar_snapshot error:", e)

def send_daily_summary() -> None:
    """Buat grafik ringkasan harian dan kirim ke Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] not configured, skip daily summary")
        return

    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """
                SELECT HOUR(created_at) AS h,
                       SUM(ldr_state = 1) AS dark_count,
                       COUNT(*) AS total_count
                FROM ldr_readings
                WHERE DATE(created_at) = CURDATE()
                GROUP BY HOUR(created_at)
                ORDER BY h
                """
            )
            rows: List[Dict[str, Any]] = cur.fetchall()
        finally:
            cur.close()

    if not rows:
        send_telegram("Ringkasan harian: belum ada data untuk hari ini.")
        return

    hours = [r["h"] for r in rows]
    dark = [r["dark_count"] for r in rows]
    total = [r["total_count"] for r in rows]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(hours, total, label="Total scan")
    ax.plot(hours, dark, label="Gelap (state=1)")
    ax.set_xlabel("Jam")
    ax.set_ylabel("Jumlah")
    ax.set_title("Ringkasan Harian LDR (hari ini)")
    ax.set_xticks(hours)
    ax.grid(alpha=0.2)
    ax.legend()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {"photo": ("summary.png", buf, "image/png")}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": "📈 Ringkasan harian LDR"}
    try:
        r = requests.post(url, data=data, files=files, timeout=10)
        if not r.ok:
            print("[telegram] send_daily_summary failed:", r.status_code, r.text)
    except Exception as e:
        print("[telegram] send_daily_summary error:", e)

# init pool
init_mysql(app)

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

# ---------------- API INSERT ----------------
@app.post("/api/ldr/insert")
def insert_ldr():
    """
    Body JSON (contoh):
    {
      "device_id": "esp32-001",
      "angle_deg": 0..180,
      "ldr_state": 0|1,
      "raw_value": 0..4095 (opsional),
      "level": 0|1|2      # opsional; 2 = MERAH (gelap lama)
    }
    """
    global LAST_ALERT_TS

    data = request.get_json(silent=True) or {}
    try:
        device_id = data.get("device_id", "esp32-001")
        angle_deg = int(data["angle_deg"])
        ldr_state = int(data["ldr_state"])
        raw_value = data.get("raw_value")
        if raw_value is not None:
            raw_value = int(raw_value)

        # level dari ESP32 (0=green,1=yellow,2=red). Jika belum ada, pakai -1
        level = int(data.get("level", -1))

        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute(
                    "INSERT INTO ldr_readings(device_id, angle_deg, ldr_state, raw_value) "
                    "VALUES (%s,%s,%s,%s)",
                    (device_id, angle_deg, ldr_state, raw_value),
                )
                conn.commit()
            finally:
                cur.close()

        # --- Logika kapan dianggap MERAH ---
        # 1) Kalau level==2 dari perangkat → jelas MERAH
        # 2) Fallback kalau firmware lama (tanpa level): sudut 80/100 & ldr_state=1
        is_red = False  # menentukan apakah kondisi dianggap merah
        if level == 2:
            is_red = True
        elif level == -1 and (ldr_state == 1 and angle_deg in (80, 100)):
            is_red = True

        # --- Trigger Telegram hanya saat MERAH + cooldown ---
        now_ts = time.time()
        if is_red and (now_ts - LAST_ALERT_TS) > ALERT_COOLDOWN_SEC:
            msg = (
                "*ALERT LDR MERAH (GELAP LAMA)*\n"
                f"Device : `{device_id}`\n"
                f"Sudut  : *{angle_deg}°*\n"
                f"State  : GELAP\n"
                f"Level  : {level if level != -1 else 'fallback'}\n"
                f"Raw    : {raw_value if raw_value is not None else '-'}"
            )
            send_telegram(msg)
            LAST_ALERT_TS = now_ts

        return jsonify({"ok": True}), 200
    except Exception as e:
        print("insert_ldr error:", e)
        return jsonify({"ok": False, "message": str(e)}), 400

# --------------- API QUERY DATA -------------
@app.get("/api/ldr/latest")
def latest():
    n = int(request.args.get("n", 180))
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT angle_deg, ldr_state, raw_value, created_at "
                "FROM ldr_readings ORDER BY id DESC LIMIT %s", (n,)
            )
            rows: List[Dict[str, Any]] = cur.fetchall()
        finally:
            cur.close()
    return jsonify(rows), 200

# --------------- API SETTINGS ---------------
@app.get("/api/settings")
def get_settings():
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM settings WHERE id=1")
            row = cur.fetchone()
        finally:
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
        try:
            cur.execute(f"UPDATE settings SET {', '.join(fields)} WHERE id=%s", params)
            conn.commit()
        finally:
            cur.close()
    return jsonify({"ok": True}), 200

# -------------- API COMMAND DEVICE ----------
@app.get("/api/servo/target")
def servo_target():
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT servo_mode, servo_target FROM settings WHERE id=1")
            s = cur.fetchone()
        finally:
            cur.close()
    target = -1 if s["servo_mode"] == "auto" else int(s["servo_target"])
    return jsonify({"target": target}), 200

# ------------- API EXPORT CSV -------------
@app.get("/api/ldr/export.csv")
def export_csv():
    from io import StringIO
    import csv

    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT id,device_id,angle_deg,ldr_state,raw_value,created_at "
                "FROM ldr_readings ORDER BY id DESC LIMIT 2000"
            )
            rows: List[Dict[str, Any]] = cur.fetchall()
        finally:
            cur.close()

    si = StringIO()
    w = csv.writer(si)
    w.writerow(["id", "device_id", "angle_deg", "ldr_state", "raw_value", "created_at"])
    for r in rows:
        w.writerow([
            r["id"],
            r["device_id"],
            r["angle_deg"],
            r["ldr_state"],
            r["raw_value"] or "",
            r["created_at"],
        ])

    return (
        si.getvalue(),
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=ldr_readings.csv",
        },
    )

# ------------- API NOTIFY TELEGRAM -------------
@app.get("/api/notify/radar")
def notify_radar():
    """Trigger manual kirim radar snapshot ke Telegram."""
    send_radar_snapshot()
    return jsonify({"ok": True}), 200

@app.get("/api/notify/daily")
def notify_daily():
    """Trigger manual kirim ringkasan harian ke Telegram."""
    send_daily_summary()
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100, debug=True)
# telegram_worker.py
import os
import time
import io
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_BOT_TOKEN = "8306549722:AAFZCTYXPOskgAposVcL78fTr12cT-Etxuw"
API_BASE = os.getenv("IOT_API_BASE", "http://127.0.0.1:5100")  # alamat Flask

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN belum diset di .env")

TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def tg_get_updates(offset=None, timeout=30):
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=timeout + 5)
    return r.json()


def tg_send_message(chat_id, text):
    r = requests.post(
        f"{TG_BASE}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    if not r.ok:
        print("Failed send msg:", r.status_code, r.text)


def tg_send_photo(chat_id, image_bytes, caption=None, filename="radar.png"):
    """
    Kirim gambar ke Telegram menggunakan sendPhoto.
    image_bytes: bytes PNG yang diterima dari API Flask.
    """
    files = {"photo": (filename, image_bytes, "image/png")}
    data = {
        "chat_id": chat_id,
    }
    if caption:
        data["caption"] = caption

    r = requests.post(
        f"{TG_BASE}/sendPhoto",
        data=data,
        files=files,
        timeout=20,
    )
    if not r.ok:
        print("Failed send photo:", r.status_code, r.text)


def handle_command(chat_id, text):
    text = text.strip()
    if text in ("/start", "/help"):
        tg_send_message(
            chat_id,
            "IoT Radar Bot siap.\n\n"
            "Perintah yang tersedia:\n"
            "/start   - Tampilkan pesan bantuan ini\n"
            "/help    - Tampilkan pesan bantuan ini\n"
            "/status  - 5 data terbaru sensor\n"
            "/summary - Ringkasan AI pola gelap/terang\n"
            "/radar   - Kirim gambar radar terakhir\n",
        )
        return

    if text == "/status":
        try:
            r = requests.get(f"{API_BASE}/api/ldr/latest?n=5", timeout=10)
            rows = r.json()
            if not rows:
                tg_send_message(chat_id, "Belum ada data sensor.")
                return
            lines = ["*5 Data Terbaru:*"]
            for row in rows:
                t = row["created_at"]
                angle = row["angle_deg"]
                st = "GELAP" if row["ldr_state"] == 1 else "TERANG"
                lines.append(f"- {t} | {angle}° | {st}")
            tg_send_message(chat_id, "\n".join(lines))
        except Exception as e:
            tg_send_message(chat_id, f"Gagal ambil data: `{e}`")
        return

    if text == "/summary":
        try:
            r = requests.get(f"{API_BASE}/api/ldr/ai-summary?n=200", timeout=20)
            data = r.json()
            if not data.get("ok"):
                tg_send_message(chat_id, "AI summary belum tersedia / data kosong.")
                return
            tg_send_message(chat_id, "*AI Summary:*\n\n" + data["summary"])
        except Exception as e:
            tg_send_message(chat_id, f"Gagal ambil summary: `{e}`")
        return

    if text == "/radar":
        try:
            # Ambil gambar radar dari API Flask (pastikan endpoint ini sudah ada di app.py)
            r = requests.get(f"{API_BASE}/api/ldr/radar-image?n=180", timeout=30)
            if r.status_code != 200:
                tg_send_message(
                    chat_id, f"Gagal ambil gambar radar: HTTP {r.status_code}"
                )
                return

            img_bytes = r.content
            tg_send_photo(
                chat_id, img_bytes, caption="Radar LDR terbaru (data terakhir)."
            )
        except Exception as e:
            tg_send_message(chat_id, f"Gagal ambil radar: `{e}`")
        return

    # fallback jika perintah tidak dikenal
    tg_send_message(
        chat_id, "Perintah tidak dikenal. Coba /help untuk daftar perintah."
    )


def main():
    print("Starting Telegram worker...")
    offset = None
    while True:
        try:
            updates = tg_get_updates(offset=offset)
            if not updates.get("ok"):
                time.sleep(2)
                continue

            for upd in updates.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                if not text:
                    continue
                print("Got command:", chat_id, text)
                handle_command(chat_id, text)
        except Exception as e:
            print("Worker error:", e)
            time.sleep(5)  # cooldown jika error


if __name__ == "__main__":
    main()

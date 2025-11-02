from flask import Flask, request, jsonify
from db import mysql, init_mysql

app = Flask(__name__)
init_mysql(app)

@app.route('/')
def index():
  return "IoT Flask API aktif 🚀"

@app.route('/insert', methods=['POST'])
def insert_data():
  try:
    temperature = request.form.get('temperature')
    humidity = request.form.get('humidity')
    device_id = request.form.get('device_id', 'esp32-001')

    if not temperature or not humidity:
        return jsonify({"ok": False, "message": "Missing temperature or humidity"}), 400

    conn = mysql.connect()
    cursor = conn.cursor()
    sql = "INSERT INTO iot_data (temperature, humidity, device_id) VALUES (%s, %s, %s)"
    cursor.execute(sql, (temperature, humidity, device_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"ok": True, "temperature": temperature, "humidity": humidity}), 200
  except Exception as e:
    print("Error:", e)
    return jsonify({"ok": False, "message": str(e)}), 500

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)

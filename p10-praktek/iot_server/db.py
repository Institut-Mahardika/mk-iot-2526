from flask_mysql_connector import MySQL

mysql = MySQL()

def init_mysql(app):
    # Konfigurasi sesuai .env (sudah di-set di app.py)
    # Kunci yang dipakai lib ini: MYSQL_HOST, MYSQL_PORT, MYSQL_USER,
    # MYSQL_PASSWORD, MYSQL_DATABASE (alias MYSQL_DB kita)
    if "MYSQL_DATABASE" not in app.config:
        # terima alias dari app.config["MYSQL_DB"]
        app.config["MYSQL_DATABASE"] = app.config.get("MYSQL_DB")

    # Optional tuning (abaikan jika tidak perlu)
    app.config.setdefault("MYSQL_CONNECT_TIMEOUT", 10)
    mysql.init_app(app)
# db.py
import mysql.connector
from mysql.connector import pooling

_pool = None

def init_mysql(app):
    global _pool
    cfg = {
        "host": app.config["DB_HOST"],
        "port": app.config["DB_PORT"],
        "user": app.config["DB_USER"],
        "password": app.config["DB_PASS"],
        "database": app.config["DB_NAME"],
    }
    _pool = pooling.MySQLConnectionPool(
        pool_name="iot_pool",
        pool_size=app.config["DB_POOL_SIZE"],
        pool_reset_session=True,
        **cfg
    )
    # auto-migrate: pastikan tabel ada
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ldr_readings (
              id           BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
              device_id    VARCHAR(64) NOT NULL DEFAULT 'esp32-001',
              angle_deg    INT NOT NULL,
              ldr_state    TINYINT(1) NOT NULL,
              raw_value    INT NULL,
              created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX (device_id), INDEX (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
              id            TINYINT PRIMARY KEY DEFAULT 1,
              yellow_logic  VARCHAR(16) NOT NULL DEFAULT 'gelap_singkat',
              red_hold_ms   INT NOT NULL DEFAULT 1500,
              servo_mode    VARCHAR(16) NOT NULL DEFAULT 'auto',
              servo_target  INT NOT NULL DEFAULT 90,
              updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")
        cur.execute("INSERT IGNORE INTO settings (id) VALUES (1);")
        conn.commit()
        cur.close()

def get_conn():
    if _pool is None:
        raise RuntimeError("MySQL pool belum di-init. Panggil init_mysql(app) dulu.")
    return _pool.get_connection()
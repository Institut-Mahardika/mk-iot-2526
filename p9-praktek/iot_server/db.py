from mysql.connector import pooling

_pool = None

def init_mysql(app):
    global _pool
    cfg = dict(
        host=app.config["MYSQL_HOST"],
        port=app.config["MYSQL_PORT"],
        database=app.config["MYSQL_DB"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        pool_name="iot_pool",
        pool_size=app.config["MYSQL_POOL_SIZE"],
        autocommit=False,
    )
    _pool = pooling.MySQLConnectionPool(**cfg)

def get_conn():
    return _pool.get_connection()
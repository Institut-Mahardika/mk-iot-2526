from flask_mysql_connector import MySQL

mysql = MySQL()

def init_mysql(app):
  # konfigurasi koneksi ke MySQL lokal
  app.config['MYSQL_DATABASE_USER'] = 'root'
  app.config['MYSQL_DATABASE_PASSWORD'] = ''
  app.config['MYSQL_DATABASE_DB'] = 'iot_db'
  app.config['MYSQL_DATABASE_HOST'] = 'localhost'

  mysql.init_app(app)
  return mysql

# 自作モジュール
from models import *
from controllers import *

# 外部モジュール
from sqlalchemy import exc, event
from sqlalchemy.pool import Pool
from flask import Flask, send_from_directory
import secrets

# デバッグ用
from logging import error, raiseExceptions
import logging
# ログメッセージに時間を表示する
fmt = "%(asctime)s %(levelname)s %(name)s :%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)

# Init Flask app
app = Flask(__name__)

# flask側のsessionwをuser_session, SQL側のsessionをdb_sessionとする。
secret = secrets.token_urlsafe(32)
app.secret_key = secret


app.register_blueprint(company.app)
app.register_blueprint(career.app)
app.register_blueprint(officer.app)

@app.route("/robots.txt")
def display_robots_txt():
    return send_from_directory('templates','robots.txt')

'''
Helper Method
'''



# コネクションがクローズしてる時に前もってpingを起こす
@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        raise exc.DisconnectionError()
    cursor.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80, threaded=True)
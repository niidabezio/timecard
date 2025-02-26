from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import os
os.environ["TZ"] = "Asia/Tokyo"

app = Flask(__name__)

# ✅ セッションの秘密キーを設定（ランダムな文字列でOK）
app.config["SECRET_KEY"] = "supersecretkey123"  # 🔑 ここに任意の秘密キーを設定

# ✅ データベース設定
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ✅ Flask-Login の設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

from routes import *

if __name__ == "__main__":
    app.run(debug=True)


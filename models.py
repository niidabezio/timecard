from app import db
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin  # ✅ 追加


class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    clock_in = db.Column(db.Time, nullable=True)
    clock_out = db.Column(db.Time, nullable=True)

    staff = db.relationship('Staff', backref=db.backref('attendances', lazy=True))  # ← 追加！

class WorkSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    work_month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    total_hours = db.Column(db.Float, nullable=False)
    salary = db.Column(db.Integer, nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_text = db.Column(db.String(255), nullable=False)

# ✅ ログイン用のユーザーモデルを追加
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # 本番ではハッシュ化推奨
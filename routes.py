# 1. Python標準ライブラリ
import random
from datetime import datetime

# 2. サードパーティ（外部ライブラリ）
import requests
import pandas as pd  # ✅ エクセル/PDF出力のために追加
from io import BytesIO
from sqlalchemy.sql import func

# 3. Flask関連のインポート
from flask import send_file, render_template, request, redirect, url_for, flash

# 4. 自作モジュール
from app import app, db
from models import Staff, Attendance, WorkSummary, Message, User # ← Messageを追加
# flasl login
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import jsonify



# ✅ Flask-Login の設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # 未ログイン時のリダイレクト先

# ✅ ユーザーローダー
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ✅ ログインページ
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"入力されたパスワード: {password}")
            print(f"データベースのパスワード: {user.password}")

        if user and user.password == password:
            login_user(user, remember=True)
            return redirect(url_for("attendance"))  # ✅ ログイン後に出退勤画面へ

        flash("ログイン失敗：ユーザー名またはパスワードが間違っています", "danger")

    return render_template("login.html")


# ✅ ログアウト
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ✅ テスト用の管理者アカウント作成（初回のみ使用）
@app.route("/create_admin")
def create_admin():
    admin = User(username="admin", password="admin123")
    db.session.add(admin)
    db.session.commit()
    return "管理者アカウントを作成しました（admin / admin123）"

    
@app.route('/attendance', methods=['GET'])
def attendance():
    staff = Staff.query.all()
    selected_month = request.args.get('month', datetime.today().strftime('%Y-%m'))  # デフォルトで今月を表示

    # ✅ 最近の出勤を上に（work_date を降順ソート）
    query = Attendance.query.join(Staff).order_by(Attendance.work_date.desc(), Attendance.clock_in.desc())

    # ✅ 月ごとにフィルタリング
    if selected_month:
        query = query.filter(func.strftime('%Y-%m', Attendance.work_date) == selected_month)

    attendance_records = query.all()

    # 時間を「時:分」フォーマットに変換
    for record in attendance_records:
        record.clock_in = record.clock_in.strftime('%H:%M')
        if record.clock_out:
            record.clock_out = record.clock_out.strftime('%H:%M')

    return render_template('attendance.html', staff=staff, attendance_records=attendance_records, selected_month=selected_month)



@app.route('/attendance/edit/<int:attendance_id>', methods=['GET', 'POST'])
def edit_attendance(attendance_id):
    record = Attendance.query.get(attendance_id)

    if request.method == 'POST':
        password = request.form.get('password')
        new_clock_in = request.form.get('clock_in')
        new_clock_out = request.form.get('clock_out')

        # ✅ 簡単なパスワードチェック
        if password == "1234":  # 修正用パスワード（自由に変更可）
            if new_clock_in:
                record.clock_in = datetime.strptime(new_clock_in, '%H:%M').time()
            if new_clock_out:
                record.clock_out = datetime.strptime(new_clock_out, '%H:%M').time()
            db.session.commit()
            return redirect(url_for('attendance'))
        else:
            return render_template('edit_attendance.html', record=record, error="パスワードが違います！")

    return render_template('edit_attendance.html', record=record)
@app.route('/staff')
def staff_list():
    staff = Staff.query.all()
    return render_template('staff.html', staff=staff)

@app.route('/staff/add', methods=['POST'])
def add_staff():
    name = request.form.get('name')
    if name:
        new_staff = Staff(name=name)
        db.session.add(new_staff)
        db.session.commit()
    return redirect(url_for('staff_list'))

# 勤務時間と給与の集計ページ
HOURLY_WAGE = 1000  # ✅ 時給を設定（自由に変更可）

@app.route('/staff/delete/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    staff = Staff.query.get(staff_id)

    if staff:
        # ✅ 先に出勤記録を削除（外部キー制約を回避）
        Attendance.query.filter_by(staff_id=staff_id).delete()
        db.session.delete(staff)
        db.session.commit()

    return redirect(url_for('staff_list'))


@app.route('/summary', methods=['GET', 'POST'])
def work_summary():
    staff_list = Staff.query.all()
    results = []

    if request.method == 'POST':
        staff_id = request.form.get('staff_id')
        work_month = request.form.get('work_month')

        query = db.session.query(
            Attendance.staff_id,
            Staff.name,
            Attendance.work_date,
            func.strftime('%H:%M', Attendance.clock_in).label("clock_in"),
            func.strftime('%H:%M', Attendance.clock_out).label("clock_out"),
            (func.julianday(Attendance.clock_out) - func.julianday(Attendance.clock_in)) * 24
        ).join(Staff).filter(
            Attendance.clock_out.isnot(None)  # 退勤が記録されているものだけ
        )

        if staff_id:
            query = query.filter(Attendance.staff_id == staff_id)

        if work_month:
            query = query.filter(func.strftime('%Y-%m', Attendance.work_date) == work_month)

        records = query.all()

        staff_hours = {}
        for record in records:
            work_date = record.work_date
            work_time = record[5] if record[5] is not None else 0  # 労働時間（時間単位）
            salary = work_time * HOURLY_WAGE  # ✅ 給与計算

            if record.staff_id not in staff_hours:
                staff_hours[record.staff_id] = {
                    "name": record.name,
                    "total_hours": 0,
                    "total_salary": 0,
                    "days": []
                }

            staff_hours[record.staff_id]["total_hours"] += work_time
            staff_hours[record.staff_id]["total_salary"] += salary  # ✅ 月の合計給与
            staff_hours[record.staff_id]["days"].append({
                "date": work_date,
                "clock_in": record.clock_in,
                "clock_out": record.clock_out,
                "work_time": round(work_time, 2),
                "salary": round(salary, 2)  # ✅ 日ごとの給与
            })

        results = list(staff_hours.values())

    return render_template('summary.html', staff_list=staff_list, results=results)

# メッセージ管理ページ
@app.route('/messages')
def message_list():
    messages = Message.query.all()  # メッセージ一覧を取得
    staff_list = Staff.query.all()  # ✅ スタッフ一覧を取得して `messages.html` に渡す
    return render_template('messages.html', messages=messages, staff_list=staff_list)


# メッセージの追加
@app.route('/messages/add', methods=['POST'])
def add_message():
    message_text = request.form.get('message_text')
    if message_text:
        new_message = Message(message_text=message_text)
        db.session.add(new_message)
        db.session.commit()
    return redirect(url_for('message_list'))

# メッセージの削除
@app.route('/messages/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    message = Message.query.get(message_id)
    if message:
        db.session.delete(message)
        db.session.commit()
    return redirect(url_for('message_list'))

@app.route('/attendance/clock_in', methods=['POST'])
def clock_in():
    staff_id = request.form.get('staff_id')
    if staff_id:
        now = datetime.now().time()  # ✅ `datetime.time` 型で取得
        new_record = Attendance(
            staff_id=staff_id,
            work_date=datetime.today().date(),
            clock_in=now,  # ✅ 文字列ではなく `datetime.time` を保存
            clock_out=None
        )
        db.session.add(new_record)
        db.session.commit()

    return redirect(url_for('attendance'))

        # ✅ 出勤後に「出勤しました」ページへリダイレクト
    return redirect(url_for('clock_in_success', staff_id=staff_id))

    return redirect(url_for('attendance'))  # ✅ 失敗した場合は元のページへ



@app.route('/attendance/clock_out/<int:attendance_id>', methods=['POST'])
def clock_out(attendance_id):
    record = Attendance.query.get(attendance_id)
    if record and record.clock_out is None:  # まだ退勤していない場合
        record.clock_out = datetime.now().time()
        db.session.commit()
    return redirect(url_for('attendance'))

@app.route('/attendance/delete/<int:attendance_id>', methods=['POST'])
def delete_attendance(attendance_id):
    record = Attendance.query.get(attendance_id)
    if record:
        db.session.delete(record)
        db.session.commit()
    return redirect(url_for('attendance'))

@app.route('/export_summary/<file_type>', methods=['POST'])
def export_summary(file_type):
    # ダミーデータ（本来はDBから取得）
    data = {
        "スタッフ名": ["田中", "鈴木", "佐藤"],
        "月の合計労働時間": [160, 140, 180],
        "月の給与（円）": [160000, 140000, 180000]
    }

    df = pd.DataFrame(data)

    if file_type == "excel":
        file_path = "summary.xlsx"
        df.to_excel(file_path, index=False)
        return send_file(file_path, as_attachment=True)

    else:
        return "現在 PDF 出力は無効になっています", 400

@app.route('/attendance/clock_in_success/<int:staff_id>')
def clock_in_success(staff_id):
    staff = Staff.query.get(staff_id)
    messages = Message.query.all()  # ✅ メッセージ管理のメッセージを取得
    return render_template('clock_in_success.html', staff=staff, messages=messages)

@app.route("/")
def home():
    return render_template("index.html")  # ✅ `index.html` を表示

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500
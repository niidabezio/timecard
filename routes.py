import random
import requests
import pandas as pd  # ✅ エクセル/PDF出力のために追加
from flask import send_file
from flask import render_template, request, redirect, url_for
from app import app, db
from models import Staff, Attendance, WorkSummary, Message  # ← Messageを追加
from datetime import datetime
from sqlalchemy.sql import func


    
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
    messages = Message.query.all()
    return render_template('messages.html', messages=messages)

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
        new_record = Attendance(
            staff_id=staff_id,
            work_date=datetime.today().date(),
            clock_in=datetime.now().time(),
            clock_out=None
        )
        db.session.add(new_record)
        db.session.commit()

        # ✅ 出勤後に「message.html」へリダイレクト
        return redirect(url_for('message', staff_id=staff_id))

    return redirect(url_for('attendance'))  # ✅ 失敗した場合は元のページへ


    


    return redirect(url_for('attendance'))


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
    elif file_type == "pdf":
        file_path = "summary.pdf"
        df.to_csv("summary.csv", index=False)  # PDF変換前にCSV保存
        import pdfkit
        pdfkit.from_file("summary.csv", file_path)  # CSVをPDFに変換
    else:
        return "無効なファイル形式", 400

    return send_file(file_path, as_attachment=True)

@app.route('/attendance/message/<int:staff_id>')
def message(staff_id):
    staff = Staff.query.get(staff_id)
    return render_template('message.html', staff=staff)

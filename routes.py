import random
import requests
from flask import render_template, request, redirect, url_for
from app import app, db
from models import Staff, Attendance, WorkSummary, Message  # ← Messageを追加
from datetime import datetime
from sqlalchemy.sql import func


    
@app.route('/attendance')
def attendance():
    staff = Staff.query.all()
    attendance_records = Attendance.query.all()
    messages = Message.query.all()  # ✅ 追加：全メッセージを取得

    # 時間を「時:分」フォーマットに変換
    for record in attendance_records:
        record.clock_in = record.clock_in.strftime('%H:%M')
        if record.clock_out:
            record.clock_out = record.clock_out.strftime('%H:%M')

    return render_template('attendance.html', staff=staff, attendance_records=attendance_records, messages=messages)



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



# 時給の設定（例: 1000円）
HOURLY_WAGE = 1000

# 勤務時間と給与の集計ページ
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
            func.julianday(Attendance.clock_out) - func.julianday(Attendance.clock_in)
        ).join(Staff).filter(
            Attendance.clock_out.isnot(None)  # 退勤が記録されているものだけ
        )

        if staff_id:
            query = query.filter(Attendance.staff_id == staff_id)

        if work_month:
            query = query.filter(func.strftime('%Y-%m', Attendance.work_date) == work_month)

        records = query.all()

        # 各スタッフの月合計時間を計算
        staff_hours = {}
        for record in records:
            work_date = record.work_date
            work_time = (record[5] * 24) if record[5] is not None else 0  # 日の労働時間（時間単位）

            if record.staff_id not in staff_hours:
                staff_hours[record.staff_id] = {"name": record.name, "total_hours": 0, "days": []}

            staff_hours[record.staff_id]["total_hours"] += work_time
            staff_hours[record.staff_id]["days"].append({
                "date": work_date,
                "clock_in": record.clock_in,
                "clock_out": record.clock_out,
                "work_time": round(work_time, 2)
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

        # ✅ ランダムな登録メッセージ
        messages = Message.query.all()
        random_message = random.choice(messages).message_text if messages else "おはようございます！"

    


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

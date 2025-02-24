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
    selected_staff_id = request.form.get('staff_id')
    selected_month = request.form.get('work_month')

    query = db.session.query(
        Attendance.staff_id,
        func.strftime('%Y-%m', Attendance.work_date).label('work_month'),
        func.sum(
            func.julianday(Attendance.clock_out) - func.julianday(Attendance.clock_in)
        ).label('total_hours')
    ).filter(Attendance.clock_out.isnot(None))

    if selected_staff_id:
        query = query.filter(Attendance.staff_id == selected_staff_id)
    if selected_month:
        query = query.filter(func.strftime('%Y-%m', Attendance.work_date) == selected_month)

    query = query.group_by(Attendance.staff_id, 'work_month')
    summaries = query.all()

    results = []
    for summary in summaries:
        total_hours = summary.total_hours * 24  # 日数を時間に変換
        salary = int(total_hours * HOURLY_WAGE)
        staff_name = Staff.query.get(summary.staff_id).name
        results.append({
            'staff_name': staff_name,
            'work_month': summary.work_month,
            'total_hours': round(total_hours, 2),
            'salary': salary
        })

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

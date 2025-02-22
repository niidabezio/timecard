from flask import render_template, request, redirect, url_for
from app import app, db
from models import Staff, Attendance, WorkSummary
from datetime import datetime
from sqlalchemy.sql import func

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
    ).filter(Attendance.clock_out.isnot(None))  # 退勤しているデータのみ集計

    if selected_staff_id:
        query = query.filter(Attendance.staff_id == selected_staff_id)
    if selected_month:
        query = query.filter(func.strftime('%Y-%m', Attendance.work_date) == selected_month)

    query = query.group_by(Attendance.staff_id, 'work_month')
    summaries = query.all()

    # 集計結果をリストに格納
    results = []
    for summary in summaries:
        total_hours = summary.total_hours * 24  # 日数を時間に変換
        salary = int(total_hours * HOURLY_WAGE)  # 給与計算
        staff_name = Staff.query.get(summary.staff_id).name
        results.append({
            'staff_name': staff_name,
            'work_month': summary.work_month,
            'total_hours': round(total_hours, 2),
            'salary': salary
        })

    return render_template('summary.html', staff_list=staff_list, results=results)



# 出退勤画面（出勤・退勤ボタンあり）
@app.route('/attendance')
def attendance():
    staff = Staff.query.all()  # スタッフ一覧を取得
    attendance_records = Attendance.query.all()  # 全ての出退勤記録を取得
    return render_template('attendance.html', staff=staff, attendance_records=attendance_records)

# 出勤ボタンを押したとき
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
    return redirect(url_for('attendance'))

# 退勤ボタンを押したとき
@app.route('/attendance/clock_out/<int:attendance_id>', methods=['POST'])
def clock_out(attendance_id):
    record = Attendance.query.get(attendance_id)
    if record and record.clock_out is None:  # まだ退勤していない場合
        record.clock_out = datetime.now().time()
        db.session.commit()
    return redirect(url_for('attendance'))

# スタッフ一覧表示
@app.route('/staff')
def staff_list():
    staff = Staff.query.all()  # データベースから全スタッフ取得
    return render_template('staff.html', staff=staff)

# スタッフ登録
@app.route('/staff/add', methods=['POST'])
def add_staff():
    name = request.form.get('name')
    if name:
        new_staff = Staff(name=name)
        db.session.add(new_staff)
        db.session.commit()
    return redirect(url_for('staff_list'))

from datetime import datetime, timedelta


def calculate_attendance(attendance):
    schedule = ShiftSchedule.objects.filter(
        employee=attendance.employee,
        date=attendance.date
    ).first()

    if not schedule:
        return

    shift = schedule.shift

    if not attendance.check_in:
        attendance.status = 'absent'
        return

    shift_start = datetime.combine(attendance.date, shift.start_time)
    shift_end = datetime.combine(attendance.date, shift.end_time)

    # =========================
    # ⏱️ LATE
    # =========================
    if attendance.check_in > shift_start:
        delta = attendance.check_in - shift_start
        attendance.late_minutes = int(delta.total_seconds() / 60)
        attendance.status = 'late'

    # =========================
    # ⏱️ WORKED
    # =========================
    if attendance.check_out:
        worked = attendance.check_out - attendance.check_in
        attendance.worked_minutes = int(worked.total_seconds() / 60)

    # =========================
    # ⏱️ OVERTIME
    # =========================
    if attendance.check_out and attendance.check_out > shift_end:
        overtime = attendance.check_out - shift_end
        attendance.overtime_minutes = int(overtime.total_seconds() / 60)

    attendance.save()


def check_in(employee):
    today = datetime.now().date()

    attendance, _ = Attendance.objects.get_or_create(
        employee=employee,
        date=today
    )

    attendance.check_in = datetime.now()
    calculate_attendance(attendance)

    return attendance



def check_out(employee):
    today = datetime.now().date()

    attendance = Attendance.objects.get(
        employee=employee,
        date=today
    )

    attendance.check_out = datetime.now()
    calculate_attendance(attendance)

    return attendance
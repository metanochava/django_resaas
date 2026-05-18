def calculate_salary(employee, base_salary, overtime_rate=1.5, late_penalty=0.5):
    attendances = employee.attendances.all()

    total_overtime = sum(a.overtime_minutes for a in attendances)
    total_late = sum(a.late_minutes for a in attendances)

    # =========================
    # 💰 CALCULATION
    # =========================
    overtime_pay = total_overtime * overtime_rate
    late_discount = total_late * late_penalty

    final_salary = base_salary + overtime_pay - late_discount

    return {
        "base_salary": base_salary,
        "overtime_minutes": total_overtime,
        "late_minutes": total_late,
        "overtime_pay": overtime_pay,
        "late_discount": late_discount,
        "final_salary": final_salary
    }
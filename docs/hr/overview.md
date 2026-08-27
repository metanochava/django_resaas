# The `hr` App

`hr` is a payroll/HR domain app built on top of `django_resaas`'s primitives (its models inherit
the same `BaseModel`/tenant conventions - see
[`docs/api/public-api-reference.md`](../api/public-api-reference.md)). It is **not optional** from
the framework's point of view: `django_resaas/urls.py` unconditionally does
`include('hr.urls')`, so an installation that includes `django_resaas` also needs `hr` installed
(both are listed in `src/dev/settings.py`'s `MY_APPS`).

## Models (`src/hr/models/__init__.py`)

-   `Employee`, `Department`, `JobPosition` - core organizational structure. `Employee` links to
    `Person` (from `django_resaas`), an optional `manager` (self-referential), and a `position`.
-   `Specialty`, `EmployeeSpecialty` - skills/specialties an employee can hold.
-   `Shift`, `EmployeeShift`, `ShiftSchedule`, `Attendance` - work-schedule and clock-in/out
    tracking. `Attendance` stores `check_in`/`check_out`, `late_minutes`, `overtime_minutes`,
    `worked_minutes` and a `status` (e.g. `absent`, `late`).
-   `SalaryComponent`, `EmployeeSalary` - configurable pay components per employee.
-   `PayrollPeriod`, `Payroll`, `PayrollItem`, `Payslip` - payroll runs and their line items.

## Business logic

### `hr/services/attendance_service.py`

-   `calculate_attendance(attendance)` - looks up the `ShiftSchedule` for the attendance's
    employee/date; if none exists, does nothing. Otherwise: marks the attendance `absent` if
    there's no `check_in`; if `check_in` is after the shift's `start_time`, computes
    `late_minutes` and marks it `late`; if `check_out` is set, computes `worked_minutes`; if
    `check_out` is after the shift's `end_time`, computes `overtime_minutes`. Saves the instance.
-   `check_in(employee)` / `check_out(employee)` - get-or-create (for check-in) or fetch (for
    check-out) today's `Attendance` row for the employee, stamp the current time, and call
    `calculate_attendance()`.

    **Known issue:** this module uses `ShiftSchedule` and `Attendance` without importing them -
    both are undefined names in `hr/services/attendance_service.py` as written, so calling
    `check_in()`/`check_out()`/`calculate_attendance()` directly will raise `NameError` unless
    something else injects those names into the module's namespace first. Flagging this as
    pre-existing, out of scope for the professionalization pass (no business-logic changes) - see
    the top-level plan for why this was left untouched.

### `hr/services/payroll_service.py`

-   `calculate_salary(employee, base_salary, overtime_rate=1.5, late_penalty=0.5)` - sums
    `overtime_minutes` and `late_minutes` across all of the employee's `attendances`, computes
    `overtime_pay = total_overtime * overtime_rate` and `late_discount = total_late *
    late_penalty`, and returns `final_salary = base_salary + overtime_pay - late_discount` along
    with the intermediate figures (`base_salary`, `overtime_minutes`, `late_minutes`,
    `overtime_pay`, `late_discount`, `final_salary`) as a dict. Note the units mismatch: overtime
    and late minutes are multiplied directly by a rate/penalty with no explicit conversion to
    hours or a currency-per-minute basis - callers should treat `overtime_rate`/`late_penalty` as
    already being "per minute" figures, not "per hour" ones.

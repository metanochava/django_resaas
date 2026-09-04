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
    tracking. `Attendance` stores `check_in`/`check_out`, `source` (Manual/Web/Mobile/Biometric/
    RFID/API/External Device - only Manual/Web are actually produced today, the rest exist so the
    field never needs a migration when a real integration shows up), `late_minutes`,
    `early_departure_minutes`, `overtime_minutes`, `worked_minutes` and a `status` (`present`/
    `absent`/`late`).
-   `Holiday` - Entity-wide (`is_entity_wide=True`, the default) or Branch-scoped, and either a
    fixed date (`is_recurring=False`) or a recurring one matched by month/day across years
    (`is_recurring=True`, e.g. Christmas). Queried via `hr/services/holiday_service.is_holiday(entity, branch, date)`.
-   `JobGrade` - level/seniority independent of `JobPosition` (Junior/Senior/... ordered by
    `level`), assignable to an `Employee`.
-   `SalaryComponent`, `EmployeeSalary` - configurable pay components per employee.
-   `PayrollPeriod`, `Payroll`, `PayrollItem`, `Payslip` - payroll runs and their line items.

## Business logic

### `hr/services/attendance_service.py`

-   `calculate_attendance(attendance)` - looks up the `ShiftSchedule` for the attendance's
    employee/date; if none exists, just saves the instance as-is (see the fixed bug below) and
    returns. Otherwise: marks the attendance `absent` if there's no `check_in`; if `check_in` is
    after the shift's `start_time` (shift bounds computed by `_shift_bounds()`, which accounts for
    shifts crossing midnight - `end_time <= start_time` means the shift ends the next day, e.g.
    23:00-07:00), computes `late_minutes` and marks it `late`; if `check_out` is set, computes
    `worked_minutes`, and either `overtime_minutes` (checked out after the shift ended) or
    `early_departure_minutes` (checked out before it ended) - never both. Saves the instance.
-   `check_in(employee, *, source=AttendanceSource.MANUAL, actor=None)` /
    `check_out(employee, *, actor=None)` - get-or-create (check-in) or fetch (check-out) today's
    `Attendance` row for the employee, stamp `timezone.now()`, call `calculate_attendance()`, and
    emit `hr.attendance.checked_in` / `hr.attendance.checked_out` (plus
    `hr.attendance.overtime_recorded` when `overtime_minutes > 0`) via `EventDispatcher.emit()` -
    `hr`'s first real use of the event system. Both raise `AttendanceError` (not `NameError`
    anymore - see below) for: a second check-in the same day while one is already open, a
    check-out with no open check-in, or a second check-out. The `check_in`/`check_out`
    `@resaas_action`s on `EmployeeAPIView` (`hr/views/employee.py`) wrap these in
    `transaction.atomic()` and turn `AttendanceError` into an HTTP 400.

    **Fixed (Fase 2):** this module used to reference `ShiftSchedule`/`Attendance` without
    importing either name - both were undefined, so calling `check_in()`/`check_out()`/
    `calculate_attendance()` raised `NameError`. Also fixed as part of the same change: the
    no-`ShiftSchedule` branch of `calculate_attendance()` used to `return` before ever calling
    `.save()`, so a `check_in`/`check_out` stamped for an employee with no shift scheduled was
    silently never persisted. All datetimes go through `django.utils.timezone`
    (`timezone.now()`/`timezone.localdate()`/`timezone.make_aware()`), not the naive
    `datetime.now()` the original code used - this project runs with `USE_TZ=True`, so a naive
    value compared against one read back from the DB (timezone-aware) raises `TypeError`.

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

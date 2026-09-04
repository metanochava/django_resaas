# hr/views/__init__.py
#
# Importing every view module here runs their @registerView decorators,
# which populate VIEW_REGISTRY. Without this, only view modules imported
# elsewhere (e.g. by hr/urls.py) ever register, so build_saas_urls()
# silently skips the rest of hr's resources.

from .employee import EmployeeAPIView
from .department import DepartmentAPIView
from .job_position import JobPositionAPIView
from .job_grade import JobGradeAPIView
from .contract import ContractAPIView

from .specialty import SpecialtyAPIView
from .employee_specialty import EmployeeSpecialtyAPIView

from .shift import ShiftAPIView
from .employee_shift import EmployeeShiftAPIView
from .shift_schedule import ShiftScheduleAPIView
from .attendance import AttendanceAPIView
from .holiday import HolidayAPIView

from .salary_component import SalaryComponentAPIView
from .employee_salary import EmployeeSalaryAPIView

from .payroll_period import PayrollPeriodAPIView
from .payroll import PayrollAPIView
from .payroll_item import PayrollItemAPIView

from .payslip import PayslipAPIView

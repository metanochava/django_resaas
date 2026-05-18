from django.contrib import admin
from django_resaas.core.base.admin import BaseAdmin, all_fields

admin.site.site_title = 'HR'
admin.site.index_title = 'HR'


# =========================
# EMPLOYEE
# =========================
from hr.models.employee import Employee

@admin.register(Employee)
class EmployeeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# DEPARTMENT
# =========================
from hr.models.department import Department

@admin.register(Department)
class DepartmentAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# JOB POSITION
# =========================
from hr.models.job_position import JobPosition

@admin.register(JobPosition)
class JobPositionAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SPECIALTY
# =========================
from hr.models.specialty import Specialty

@admin.register(Specialty)
class SpecialtyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SPECIALTY
# =========================
from hr.models.employee_specialty import EmployeeSpecialty

@admin.register(EmployeeSpecialty)
class EmployeeSpecialtyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SHIFT
# =========================
from hr.models.shift import Shift

@admin.register(Shift)
class ShiftAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SHIFT
# =========================
from hr.models.employee_shift import EmployeeShift

@admin.register(EmployeeShift)
class EmployeeShiftAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SHIFT SCHEDULE
# =========================
from hr.models.shift_schedule import ShiftSchedule

@admin.register(ShiftSchedule)
class ShiftScheduleAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# ATTENDANCE
# =========================
from hr.models.attendance import Attendance

@admin.register(Attendance)
class AttendanceAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SALARY COMPONENT
# =========================
from hr.models.salary_component import SalaryComponent

@admin.register(SalaryComponent)
class SalaryComponentAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SALARY
# =========================
from hr.models.employee_salary import EmployeeSalary

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYROLL PERIOD
# =========================
from hr.models.payroll_period import PayrollPeriod

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYROLL
# =========================
from hr.models.payroll import Payroll

@admin.register(Payroll)
class PayrollAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYROLL ITEM
# =========================
from hr.models.payroll_item import PayrollItem

@admin.register(PayrollItem)
class PayrollItemAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYSLIP
# =========================
from hr.models.payslip import Payslip

@admin.register(Payslip)
class PayslipAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
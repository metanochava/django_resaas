
from django.urls import path, include
from rest_framework import routers

from django_resaas.hr.views import (
    EmployeeAPIView,
    DepartmentAPIView,
    JobPositionAPIView,
    JobGradeAPIView,
    ContractAPIView,
    SpecialtyAPIView,
    EmployeeSpecialtyAPIView,
    ShiftAPIView,
    EmployeeShiftAPIView,
    ShiftScheduleAPIView,
    AttendanceAPIView,
    HolidayAPIView,
    SalaryComponentAPIView,
    EmployeeSalaryAPIView,
    PayrollPeriodAPIView,
    PayrollAPIView,
    PayrollItemAPIView,
    PayslipAPIView,
)


router = routers.DefaultRouter()
router.register("employees", EmployeeAPIView, basename="employees")
router.register("departments", DepartmentAPIView, basename="departments")
router.register("jobpositions", JobPositionAPIView, basename="jobpositions")
router.register("jobgrades", JobGradeAPIView, basename="jobgrades")
router.register("contracts", ContractAPIView, basename="contracts")
router.register("specialties", SpecialtyAPIView, basename="specialties")
router.register("employeespecialties", EmployeeSpecialtyAPIView, basename="employeespecialties")
router.register("shifts", ShiftAPIView, basename="shifts")
router.register("employeeshifts", EmployeeShiftAPIView, basename="employeeshifts")
router.register("shiftschedules", ShiftScheduleAPIView, basename="shiftschedules")
router.register("attendances", AttendanceAPIView, basename="attendances")
router.register("holidays", HolidayAPIView, basename="holidays")
router.register("salarycomponents", SalaryComponentAPIView, basename="salarycomponents")
router.register("employeesalaries", EmployeeSalaryAPIView, basename="employeesalaries")
router.register("payrollperiods", PayrollPeriodAPIView, basename="payrollperiods")
router.register("payrolls", PayrollAPIView, basename="payrolls")
router.register("payrollitems", PayrollItemAPIView, basename="payrollitems")
router.register("payslips", PayslipAPIView, basename="payslips")

urlpatterns = [
    path("", include(router.urls)),
]

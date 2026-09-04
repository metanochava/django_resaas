
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
    LeaveTypeAPIView,
    LeaveRequestAPIView,
    LeaveBalanceEntryAPIView,
    JobOpeningAPIView,
    CandidateAPIView,
    ApplicationAPIView,
    InterviewAPIView,
    OnboardingTemplateAPIView,
    OnboardingTemplateTaskAPIView,
    EmployeeOnboardingAPIView,
    EmployeeOnboardingTaskAPIView,
    PerformanceCycleAPIView,
    CompetencyAPIView,
    EmployeeGoalAPIView,
    PerformanceReviewAPIView,
    ReviewCompetencyRatingAPIView,
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
router.register("leavetypes", LeaveTypeAPIView, basename="leavetypes")
router.register("leaverequests", LeaveRequestAPIView, basename="leaverequests")
router.register("leavebalanceentries", LeaveBalanceEntryAPIView, basename="leavebalanceentries")
router.register("jobopenings", JobOpeningAPIView, basename="jobopenings")
router.register("candidates", CandidateAPIView, basename="candidates")
router.register("applications", ApplicationAPIView, basename="applications")
router.register("interviews", InterviewAPIView, basename="interviews")
router.register("onboardingtemplates", OnboardingTemplateAPIView, basename="onboardingtemplates")
router.register("onboardingtemplatetasks", OnboardingTemplateTaskAPIView, basename="onboardingtemplatetasks")
router.register("employeeonboardings", EmployeeOnboardingAPIView, basename="employeeonboardings")
router.register("employeeonboardingtasks", EmployeeOnboardingTaskAPIView, basename="employeeonboardingtasks")
router.register("performancecycles", PerformanceCycleAPIView, basename="performancecycles")
router.register("competencies", CompetencyAPIView, basename="competencies")
router.register("employeegoals", EmployeeGoalAPIView, basename="employeegoals")
router.register("performancereviews", PerformanceReviewAPIView, basename="performancereviews")
router.register("reviewcompetencyratings", ReviewCompetencyRatingAPIView, basename="reviewcompetencyratings")

urlpatterns = [
    path("", include(router.urls)),
]

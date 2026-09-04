from django.contrib import admin
from django_resaas.engine.core.base.admin import BaseAdmin, all_fields

admin.site.site_title = 'HR'
admin.site.index_title = 'HR'


# =========================
# EMPLOYEE
# =========================
from django_resaas.hr.models.employee import Employee

@admin.register(Employee)
class EmployeeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# DEPARTMENT
# =========================
from django_resaas.hr.models.department import Department

@admin.register(Department)
class DepartmentAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# JOB POSITION
# =========================
from django_resaas.hr.models.job_position import JobPosition

@admin.register(JobPosition)
class JobPositionAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# JOB GRADE
# =========================
from django_resaas.hr.models.job_grade import JobGrade

@admin.register(JobGrade)
class JobGradeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SPECIALTY
# =========================
from django_resaas.hr.models.specialty import Specialty

@admin.register(Specialty)
class SpecialtyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SPECIALTY
# =========================
from django_resaas.hr.models.employee_specialty import EmployeeSpecialty

@admin.register(EmployeeSpecialty)
class EmployeeSpecialtyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SHIFT
# =========================
from django_resaas.hr.models.shift import Shift

@admin.register(Shift)
class ShiftAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SHIFT
# =========================
from django_resaas.hr.models.employee_shift import EmployeeShift

@admin.register(EmployeeShift)
class EmployeeShiftAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SHIFT SCHEDULE
# =========================
from django_resaas.hr.models.shift_schedule import ShiftSchedule

@admin.register(ShiftSchedule)
class ShiftScheduleAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# ATTENDANCE
# =========================
from django_resaas.hr.models.attendance import Attendance

@admin.register(Attendance)
class AttendanceAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# HOLIDAY
# =========================
from django_resaas.hr.models.holiday import Holiday

@admin.register(Holiday)
class HolidayAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# SALARY COMPONENT
# =========================
from django_resaas.hr.models.salary_component import SalaryComponent

@admin.register(SalaryComponent)
class SalaryComponentAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SALARY
# =========================
from django_resaas.hr.models.employee_salary import EmployeeSalary

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE SALARY COMPONENT
# =========================
from django_resaas.hr.models.employee_salary_component import EmployeeSalaryComponent

@admin.register(EmployeeSalaryComponent)
class EmployeeSalaryComponentAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYROLL PERIOD
# =========================
from django_resaas.hr.models.payroll_period import PayrollPeriod

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYROLL
# =========================
from django_resaas.hr.models.payroll import Payroll

@admin.register(Payroll)
class PayrollAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYROLL ITEM
# =========================
from django_resaas.hr.models.payroll_item import PayrollItem

@admin.register(PayrollItem)
class PayrollItemAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PAYSLIP
# =========================
from django_resaas.hr.models.payslip import Payslip

@admin.register(Payslip)
class PayslipAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# LEAVE TYPE
# =========================
from django_resaas.hr.models.leave_type import LeaveType

@admin.register(LeaveType)
class LeaveTypeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# LEAVE REQUEST
# =========================
from django_resaas.hr.models.leave_request import LeaveRequest

@admin.register(LeaveRequest)
class LeaveRequestAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# LEAVE BALANCE ENTRY
# =========================
from django_resaas.hr.models.leave_balance_entry import LeaveBalanceEntry

@admin.register(LeaveBalanceEntry)
class LeaveBalanceEntryAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# JOB OPENING
# =========================
from django_resaas.hr.models.job_opening import JobOpening

@admin.register(JobOpening)
class JobOpeningAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# CANDIDATE
# =========================
from django_resaas.hr.models.candidate import Candidate

@admin.register(Candidate)
class CandidateAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# APPLICATION
# =========================
from django_resaas.hr.models.application import Application

@admin.register(Application)
class ApplicationAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# INTERVIEW
# =========================
from django_resaas.hr.models.interview import Interview

@admin.register(Interview)
class InterviewAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# ONBOARDING TEMPLATE
# =========================
from django_resaas.hr.models.onboarding_template import OnboardingTemplate

@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# ONBOARDING TEMPLATE TASK
# =========================
from django_resaas.hr.models.onboarding_template_task import OnboardingTemplateTask

@admin.register(OnboardingTemplateTask)
class OnboardingTemplateTaskAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE ONBOARDING
# =========================
from django_resaas.hr.models.employee_onboarding import EmployeeOnboarding

@admin.register(EmployeeOnboarding)
class EmployeeOnboardingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE ONBOARDING TASK
# =========================
from django_resaas.hr.models.employee_onboarding_task import EmployeeOnboardingTask

@admin.register(EmployeeOnboardingTask)
class EmployeeOnboardingTaskAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

# =========================
# PERFORMANCE CYCLE
# =========================
from django_resaas.hr.models.performance_cycle import PerformanceCycle

@admin.register(PerformanceCycle)
class PerformanceCycleAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# COMPETENCY
# =========================
from django_resaas.hr.models.competency import Competency

@admin.register(Competency)
class CompetencyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE GOAL
# =========================
from django_resaas.hr.models.employee_goal import EmployeeGoal

@admin.register(EmployeeGoal)
class EmployeeGoalAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# PERFORMANCE REVIEW
# =========================
from django_resaas.hr.models.performance_review import PerformanceReview

@admin.register(PerformanceReview)
class PerformanceReviewAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# REVIEW COMPETENCY RATING
# =========================
from django_resaas.hr.models.review_competency_rating import ReviewCompetencyRating

@admin.register(ReviewCompetencyRating)
class ReviewCompetencyRatingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# COURSE
# =========================
from django_resaas.hr.models.course import Course

@admin.register(Course)
class CourseAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# TRAINING SESSION
# =========================
from django_resaas.hr.models.training_session import TrainingSession

@admin.register(TrainingSession)
class TrainingSessionAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# EMPLOYEE TRAINING
# =========================
from django_resaas.hr.models.employee_training import EmployeeTraining

@admin.register(EmployeeTraining)
class EmployeeTrainingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# CERTIFICATION
# =========================
from django_resaas.hr.models.certification import Certification

@admin.register(Certification)
class CertificationAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

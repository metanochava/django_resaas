"""
hr/services/attendance_service.py has a real, pre-existing bug: it uses
`ShiftSchedule` and `Attendance` without importing either name, so every
function in the module raises NameError when called (documented as a known
issue in docs/hr/overview.md). These tests lock in that current behavior
rather than silently fixing it (no logic changes without confirmation).
"""
import pytest

from django_resaas.engine.models.entity import Entity
from django_resaas.engine.models.entity_type import EntityType
from django_resaas.engine.models.branch import Branch
from django_resaas.engine.models.person import Person
from django_resaas.hr.models.employee import Employee
from django_resaas.hr.services import attendance_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee(db):
    entity_type = EntityType.objects.create(name="SaaS", state=1)
    entity = Entity.objects.create(name="Tenant", entity_type=entity_type, state=1)
    branch = Branch.objects.create(name="Main", entity=entity, state=1)
    person = Person.objects.create(name="Jane", surname="Doe")

    return Employee.objects.create(
        person=person,
        code="EMP-1",
        hire_date="2024-01-01",
        entity=entity,
        branch=branch,
    )


@pytest.mark.xfail(
    strict=True,
    reason="known bug: check_in() calls Attendance.objects.get_or_create(...) "
    "but never imports Attendance -> NameError",
)
def test_check_in(employee):
    attendance_service.check_in(employee)


@pytest.mark.xfail(
    strict=True,
    reason="known bug: check_out() calls Attendance.objects.get(...) but "
    "never imports Attendance -> NameError",
)
def test_check_out(employee):
    attendance_service.check_out(employee)

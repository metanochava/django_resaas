"""Tenant fields read by role (saas/core/base/field_access.py):
the Entity is returned only to the platform Root (is_platform), the Branch
only to an Entity administrator (is_entity_admin). Writes are not restricted.
"""
from datetime import date
from types import SimpleNamespace

import pytest

from django_resaas.saas.core.base import field_access
from django_resaas.saas.core.services import group_access_service
from django_resaas.saas.models.person import Person
from dev.demo.models import Agreement, Member

pytestmark = pytest.mark.django_db

URL = "/api/demo/agreements/"


def _make_agreement(tenant):
    person = Person.objects.create(name="Role", surname="Read")
    member = Member.objects.create(
        entity=tenant["entity"], branch=tenant["branch"], person=person,
        code="MEM-TR-1", joined_on=date(2024, 1, 1),
    )
    return Agreement.objects.create(
        entity=tenant["entity"], branch=tenant["branch"], member=member,
        start_date=date(2025, 1, 1), amount=100,
    )


def _roles(monkeypatch, platform, entity_admin):
    monkeypatch.setattr(group_access_service, "is_platform", lambda request: platform)
    monkeypatch.setattr(group_access_service, "is_entity_admin", lambda request: entity_admin)
    return SimpleNamespace(user=None, entity_id=1)


def test_tenant_read_rules_are_declared_for_entity_and_branch():
    restrictions = field_access.get_field_restrictions(Agreement)

    assert restrictions["entity"] == {"view": "role:platform", "change": None}
    assert restrictions["branch"] == {"view": "role:platform_or_entity_admin", "change": None}
    # the schema still publishes only the codenames the model declares
    assert "entity" not in field_access.get_field_permissions(Agreement)


def test_root_reads_entity_and_branch_and_the_entity_admin_reads_the_branch(monkeypatch):
    tenant_fields = {"entity", "branch"}

    request = _roles(monkeypatch, platform=True, entity_admin=False)
    assert field_access.unreadable_fields(request, Agreement) & tenant_fields == set()

    request = _roles(monkeypatch, platform=False, entity_admin=True)
    assert field_access.unreadable_fields(request, Agreement) & tenant_fields == {"entity"}


def test_a_common_user_reads_neither_entity_nor_branch(monkeypatch):
    request = _roles(monkeypatch, platform=False, entity_admin=False)
    hidden = field_access.unreadable_fields(request, Agreement)

    assert {"entity", "branch"} <= hidden


def test_root_who_is_also_entity_admin_reads_both(monkeypatch):
    request = _roles(monkeypatch, platform=True, entity_admin=True)

    assert "entity" not in field_access.unreadable_fields(request, Agreement)
    assert "branch" not in field_access.unreadable_fields(request, Agreement)


def test_tenant_read_rules_never_block_writes(monkeypatch):
    request = _roles(monkeypatch, platform=False, entity_admin=False)

    assert "entity" not in field_access.unwritable_fields(request, Agreement)
    assert "branch" not in field_access.unwritable_fields(request, Agreement)


def test_the_bootstrap_root_sees_the_entity_in_the_api(bootstrap_tenant):
    from dev.demo.models import Agreement as _Agreement  # noqa: F401

    tenant = bootstrap_tenant("tr-root", modules=("demo",))
    _make_agreement(tenant)

    data = tenant["client"].get(URL).json()
    results = data["results"] if isinstance(data, dict) and "results" in data else data

    assert results, "expected at least one agreement"
    assert "entity" in results[0]


def test_the_schema_drops_only_the_tenant_fields_the_role_may_not_read(monkeypatch):
    # what model_schema filters out for each caller
    assert field_access.hidden_tenant_fields(_roles(monkeypatch, True, False), Agreement) == set()
    assert field_access.hidden_tenant_fields(_roles(monkeypatch, False, True), Agreement) == {"entity"}
    assert field_access.hidden_tenant_fields(_roles(monkeypatch, False, False), Agreement) == {"entity", "branch"}
    assert field_access.hidden_tenant_fields(_roles(monkeypatch, True, True), Agreement) == set()

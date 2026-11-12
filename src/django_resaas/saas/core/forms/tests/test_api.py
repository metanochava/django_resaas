"""Form Engine API: the layers (platform only for who keeps the platform,
an Entity's layers always its own), versions (a published one never
changes), the resolved form per Entity / Branch, server-side validation and
drafts per user."""
import uuid

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.form_definition import FormDefinition
from django_resaas.saas.models.group import Group
from django_resaas.testing import bootstrap_tenant

pytestmark = pytest.mark.django_db

BASE = "/api/django_resaas/formdefinitions/"
FORMS = "/api/django_resaas/forms/"
ADMIN = ["list_formdefinition", "view_formdefinition", "add_formdefinition", "change_formdefinition",
         "delete_formdefinition", "publish_formdefinition"]


def _client(tenant, codenames):
    group = Group.objects.create(name=f"forms-{uuid.uuid4().hex[:10]}")
    group.permissions.add(*Permission.objects.filter(codename__in=codenames))
    BranchUserGroup.objects.create(branch=tenant["branch"], user=tenant["user"], group=group)
    context = ResaasContextService.issue(user=tenant["user"], entity_id=tenant["entity"].id,
                                         branch_id=tenant["branch"].id, group_id=group.id)
    client = APIClient()
    client.force_authenticate(user=tenant["user"])
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return client


def _definition(fields=None, **extra):
    return {"schema_version": "1.0", "key": "school.enrolment", "mode": "declarative",
            "sections": [{"key": "student", "label": "Student",
                          "fields": fields or [{"name": "full_name", "type": "text", "required": True}]}], **extra}


def _publish(client, payload):
    created = client.post(BASE, payload, format="json")
    assert created.status_code == 201, created.content
    published = client.post(f"{BASE}{created.data['id']}/publish/")
    assert published.status_code in (200, 202), published.content
    return created.data


@pytest.fixture
def tenant():
    from django.apps import apps

    from django_resaas.saas.core.signals.permissions import ensure_module_permissions, MODULE_PERMISSIONS

    created = bootstrap_tenant(f"forms-{uuid.uuid4().hex[:8]}")
    # what post_migrate does in an installation: the module's own permissions
    # exist and Root holds every permission
    ensure_module_permissions("django_resaas", MODULE_PERMISSIONS["django_resaas"])
    created["root_group"].permissions.add(*Permission.objects.filter(
        codename__in=["manage_platform_formdefinition", "publish_formdefinition"]))
    return created


def test_only_the_platform_keeps_platform_forms(tenant):
    admin = _client(tenant, ADMIN)
    refused = admin.post(BASE, {"key": "school.enrolment", "level": "platform", "definition": _definition()},
                         format="json")
    assert refused.status_code == 403
    root = tenant["client"]
    assert root.post(BASE, {"key": "school.enrolment", "level": "platform", "definition": _definition()},
                     format="json").status_code == 201


def test_an_entity_layer_customises_the_platform_one_and_the_branch_its_own(tenant):
    _publish(tenant["client"], {"key": "school.enrolment", "level": "platform", "definition": _definition()})
    admin = _client(tenant, ADMIN)
    _publish(admin, {"key": "school.enrolment", "level": "entity", "definition": _definition(
        [{"name": "full_name", "required": False, "label": "Student name"},
         {"name": "previous_school", "type": "text"}])})

    resolved = admin.get(FORMS + "resolve/", {"key": "school.enrolment"}).data
    fields = resolved["definition"]["sections"][0]["fields"]
    assert [f["name"] for f in fields] == ["full_name", "previous_school"]
    assert fields[0]["required"] is True and fields[0]["label"] == "Student name"
    assert [layer["level"] for layer in resolved["layers"]] == ["platform", "entity"]

    other_branch = Branch.objects.create(name="Annex", entity=tenant["entity"])
    _publish(admin, {"key": "school.enrolment", "level": "branch", "branch": str(other_branch.id),
                     "definition": _definition([{"name": "bus_route", "type": "text"}])})
    # the caller's branch is Main: the Annex layer does not apply to it
    assert "bus_route" not in [f["name"] for f in admin.get(FORMS + "resolve/", {"key": "school.enrolment"})
                               .data["definition"]["sections"][0]["fields"]]


def test_an_entity_layer_is_always_the_callers_entity(tenant):
    other = bootstrap_tenant(f"forms-other-{uuid.uuid4().hex[:8]}")
    admin = _client(tenant, ADMIN)
    created = admin.post(BASE, {"key": "school.enrolment", "level": "entity", "entity": str(other["entity"].id),
                                "definition": _definition()}, format="json")
    assert created.status_code == 201
    assert FormDefinition.objects.get(id=created.data["id"]).entity_id == tenant["entity"].id
    foreign_branch = admin.post(BASE, {"key": "school.enrolment", "level": "branch",
                                       "branch": str(other["branch"].id), "definition": _definition()}, format="json")
    assert foreign_branch.status_code == 400
    # the other Entity sees none of it
    assert _client(other, ADMIN).get(BASE).data == [] or _client(other, ADMIN).get(BASE).data.get("results") == []


def test_a_published_version_never_changes(tenant):
    admin = _client(tenant, ADMIN)
    first = _publish(admin, {"key": "school.enrolment", "level": "entity", "definition": _definition()})
    assert admin.patch(f"{BASE}{first['id']}/", {"definition": _definition()}, format="json").status_code == 409
    assert admin.delete(f"{BASE}{first['id']}/").status_code == 409
    second = admin.post(BASE, {"key": "school.enrolment", "level": "entity", "definition": _definition()},
                        format="json")
    assert second.data["version"] == 2


def test_an_invalid_definition_is_refused(tenant):
    admin = _client(tenant, ADMIN)
    response = admin.post(BASE, {"key": "school.enrolment", "level": "entity",
                                 "definition": _definition([{"name": "x", "type": "text",
                                                             "visible_if": {"js": "alert(1)"}}])}, format="json")
    assert response.status_code == 400


def test_validate_and_drafts_for_any_member(tenant):
    _publish(tenant["client"], {"key": "school.enrolment", "level": "platform", "definition": _definition()})
    member = _client(tenant, [])

    assert member.get(FORMS + "resolve/", {"key": "missing.form"}).status_code == 404
    response = member.post(FORMS + "validate/", {"key": "school.enrolment", "data": {}}, format="json")
    assert response.data == {"valid": False, "errors": {"full_name": ["This field is required."]}}

    assert member.put(FORMS + "draft/", {"key": "school.enrolment", "data": {"full_name": "Rui"}},
                      format="json").status_code in (200, 202)
    assert member.get(FORMS + "draft/", {"key": "school.enrolment"}).data["data"] == {"full_name": "Rui"}
    # another user's draft is never served
    other = bootstrap_tenant(f"forms-member-{uuid.uuid4().hex[:8]}")
    assert other["client"].get(FORMS + "draft/", {"key": "school.enrolment"}).data["data"] is None

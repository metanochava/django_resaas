"""POST resaas/boot/ - the sign-in boot in one answer (core/services/boot_service.py):
Entities -> Branch -> profile chosen when there is nothing to ask (a still
allowed hint, else the only option), then the context, permissions, menus and
phone tabs of that profile."""
import pytest
from rest_framework.test import APIClient

from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db

URL = "/api/resaas/boot/"


def _member(tenant, username, groups=("Nurse",), state="Active"):
    """A user of the tenant's Entity and Branch with these profiles."""
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass-12345")
    EntityUser.objects.get_or_create(user=user, entity=tenant["entity"])
    BranchUser.objects.get_or_create(user=user, branch=tenant["branch"])
    made = []
    for name in groups:
        group = Group.objects.create(name=f"{name}-{username}")
        group.permissions.add(*tenant["root_group"].permissions.filter(codename="list_branch"))
        EntityGroup.objects.create(entity=tenant["entity"], group=group, state="Active")
        BranchUserGroup.objects.create(user=user, branch=tenant["branch"], group=group, state=state)
        made.append(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, made, client


def _boot(client, **body):
    response = client.post(URL, body, format="json")
    assert response.status_code in (200, 202), response.data
    return response.data


def test_one_entity_branch_and_profile_boot_in_one_answer(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-one")
    user, (nurse,), client = _member(tenant, "boot-one-nurse")

    data = _boot(client)

    assert [row["id"] for row in data["entities"]] == [str(tenant["entity"].id)]
    assert data["entity"]["id"] == str(tenant["entity"].id)
    assert data["branch"] == {"id": str(tenant["branch"].id), "name": tenant["branch"].name}
    assert data["group"]["id"] == str(nurse.id)
    assert data["context"]["context"]["group_id"] == str(nurse.id)
    assert "list_branch" in data["permissions"]
    assert isinstance(data["menus"], list) and isinstance(data["mobile_tabs"], list)


def test_the_issued_context_opens_the_profiles_endpoints(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-token")
    user, _, client = _member(tenant, "boot-token-nurse")
    token = _boot(client)["context"]["token"]

    client.credentials(HTTP_X_RESAAS_CONTEXT=token, HTTP_L="1")
    response = client.get(f"/api/django_resaas/users/{user.id}/permissions/")

    assert response.status_code == 200
    assert "list_branch" in [row["codename"] for row in response.data]


def test_two_working_profiles_stop_at_the_choice(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-choice")
    user, groups, client = _member(tenant, "boot-choice-user", groups=("Nurse", "Clerk"))

    data = _boot(client)

    assert data["branch"]["id"] == str(tenant["branch"].id)
    assert data["group"] is None and data["permissions"] is None and data["menus"] is None
    # every member also has Guest (guest_profile_service)
    working = [row["id"] for row in data["groups"] if row["name"] != "Guest"]
    assert sorted(working) == sorted(str(group.id) for group in groups)
    # the context of what was chosen: Entity and Branch, no profile
    assert data["context"]["context"]["branch_id"] == str(tenant["branch"].id)
    assert data["context"]["context"]["group_id"] is None


def test_the_last_choice_is_used_while_still_allowed(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-hint")
    user, (nurse, clerk), client = _member(tenant, "boot-hint-user", groups=("Nurse", "Clerk"))

    assert _boot(client, group_id=str(clerk.id))["group"]["id"] == str(clerk.id)

    # switched off by an Admin: the hint no longer counts
    BranchUserGroup.objects.filter(user=user, group=clerk).update(state="Inactive")
    data = _boot(client, group_id=str(clerk.id))
    assert data["group"]["id"] == str(nurse.id)
    assert [row["id"] for row in data["groups"] if row["name"] != "Guest"] == [str(nurse.id)]


def test_a_hint_of_another_entity_is_ignored(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-scope-a")
    other = bootstrap_tenant("boot-scope-b")
    user, _, client = _member(tenant, "boot-scope-user")

    data = _boot(client, entity_id=str(other["entity"].id), branch_id=str(other["branch"].id))

    assert data["entity"]["id"] == str(tenant["entity"].id)
    assert data["branch"]["id"] == str(tenant["branch"].id)


def test_several_entities_stop_at_the_entity_choice(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-many")
    other = bootstrap_tenant("boot-many-b")
    user, _, client = _member(tenant, "boot-many-user")
    EntityUser.objects.get_or_create(user=user, entity=other["entity"])

    data = _boot(client)

    assert len(data["entities"]) == 2
    assert data["entity"] is None and data["context"] is None


def test_several_branches_stop_at_the_branch_choice(bootstrap_tenant):
    tenant = bootstrap_tenant("boot-branches")
    user, _, client = _member(tenant, "boot-branches-user")
    second = Branch.objects.create(name="Second", entity=tenant["entity"])
    BranchUser.objects.get_or_create(user=user, branch=second)

    data = _boot(client)

    assert data["entity"]["id"] == str(tenant["entity"].id)
    assert data["branch"] is None and len(data["branches"]) == 2
    assert data["context"]["context"]["entity_id"] == str(tenant["entity"].id)


def test_anonymous_is_refused():
    assert APIClient().post(URL, {}, format="json").status_code in (401, 403)

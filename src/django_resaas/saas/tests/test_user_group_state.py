"""An assigned profile (BranchUserGroup) is Active or Inactive, and only an
Active one gives access: permissions, the context's profile, the profiles to
pick from, menus. A new (or restored) assignment is Active; an Admin switches
it on and off in view_employee's Profiles tab (users/{id}/groupState/)."""
import importlib
from types import SimpleNamespace
from unittest import mock

import pytest
from django.apps import apps as django_apps
from rest_framework.exceptions import PermissionDenied

from django_resaas.saas.core.base.permissions import check_permission
from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.group import Group
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db

PERMISSION_CHECK = "django_resaas.saas.data.user.views.user.isPermited"


def _url(user, action):
    return f"/api/django_resaas/users/{user.id}/{action}/"


def _member(tenant, username="member"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass-12345")
    EntityUser.objects.get_or_create(user=user, entity=tenant["entity"])
    return user


def _entity_group(tenant, name="Nurse"):
    group = Group.objects.create(name=name)
    EntityGroup.objects.create(entity=tenant["entity"], group=group, state="Active")
    return group


def _client(tenant):
    client = tenant["client"]
    client.raise_request_exception = False
    return client


def _set_state(tenant, user, group, state):
    return _client(tenant).post(_url(user, "groupState"), {"group": str(group.id), "state": state}, format="json")


# ------------------------------------------------------------------ assigned Active

class TestAssignedIsActive:

    def test_a_new_assignment_is_active_whatever_creates_it(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-default")
        row = BranchUserGroup.objects.create(user=_member(tenant), group=_entity_group(tenant), branch=tenant["branch"])

        assert row.state == "Active"

    def test_add_group_assigns_an_active_profile(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-add")
        user, nurse = _member(tenant), _entity_group(tenant)

        response = _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code in (200, 202)
        assert BranchUserGroup.objects.get(user=user, group=nurse).state == "Active"

    def test_a_restored_assignment_is_active_again(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-restore")
        user, nurse = _member(tenant), _entity_group(tenant)
        row = BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"], state="Inactive")
        row.delete()

        _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert BranchUserGroup.objects.get(user=user, group=nurse).state == "Active"


# ------------------------------------------------------------------ groupState

class TestGroupState:

    def test_switches_a_profile_off_and_on(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-toggle")
        user, nurse = _member(tenant), _entity_group(tenant)
        BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"])

        off = _set_state(tenant, user, nurse, "Inactive")
        assert off.status_code in (200, 202) and off.data["state"] == "Inactive"
        assert BranchUserGroup.objects.get(user=user, group=nurse).state == "Inactive"

        on = _set_state(tenant, user, nurse, "Active")
        assert on.data["state"] == "Active"
        row = BranchUserGroup.objects.get(user=user, group=nurse)
        assert row.state == "Active" and row.updated_by_id == tenant["user"].id

    def test_the_listing_shows_the_state(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-list")
        user, nurse = _member(tenant), _entity_group(tenant)
        BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"], state="Inactive")

        response = _client(tenant).get(_url(user, "userGroups"))

        assert [(g["name"], g["state"]) for g in response.data] == [("Nurse", "Inactive")]

    def test_an_unknown_state_is_refused(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-bad")
        user, nurse = _member(tenant), _entity_group(tenant)
        BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"])

        response = _set_state(tenant, user, nurse, "Deleted")

        assert response.status_code == 400 and response.data["error"]["code"] == "invalid_state"
        assert BranchUserGroup.objects.get(user=user, group=nurse).state == "Active"

    def test_you_cannot_switch_off_the_profile_you_are_acting_with(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-self")

        response = _set_state(tenant, tenant["user"], tenant["root_group"], "Inactive")

        assert response.status_code == 400
        assert response.data["error"]["code"] == "cannot_deactivate_own_active_group"
        assert BranchUserGroup.objects.get(user=tenant["user"], group=tenant["root_group"]).state == "Active"

    def test_what_is_not_assigned_is_a_404(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-404")

        response = _set_state(tenant, _member(tenant), _entity_group(tenant), "Inactive")

        assert response.status_code == 404 and response.data["error"]["code"] == "group_not_assigned"

    def test_another_entitys_assignment_cannot_be_touched(self, bootstrap_tenant):
        mine = bootstrap_tenant("gs-scope-a")
        theirs = bootstrap_tenant("gs-scope-b")
        user, nurse = _member(theirs, "theirs"), _entity_group(theirs)
        BranchUserGroup.objects.create(user=user, group=nurse, branch=theirs["branch"])

        response = _set_state(mine, user, nurse, "Inactive")

        assert response.status_code == 404
        assert BranchUserGroup.objects.get(user=user, group=nurse).state == "Active"

    def test_is_denied_without_permission(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-perm")
        user, nurse = _member(tenant), _entity_group(tenant)
        BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"])

        with mock.patch(PERMISSION_CHECK, return_value=False):
            response = _set_state(tenant, user, nurse, "Inactive")

        assert response.status_code == 403
        assert BranchUserGroup.objects.get(user=user, group=nurse).state == "Active"


# ------------------------------------------------------------------ Inactive gives no access

class TestInactiveGivesNoAccess:

    def _inactive_profile(self, tenant, username):
        user = _member(tenant, username)
        nurse = _entity_group(tenant)
        nurse.permissions.add(*django_apps.get_model("auth", "Permission").objects.filter(codename="list_branch"))
        row = BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"])
        return user, nurse, row

    def _request(self, tenant, user, group):
        return SimpleNamespace(
            user=user, entity_type_id=tenant["entity"].entity_type_id, entity_id=tenant["entity"].id,
            branch_id=tenant["branch"].id, group_id=group.id,
        )

    def test_its_permissions_stop_counting(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-perms")
        user, nurse, row = self._inactive_profile(tenant, "nurse-perms")
        request = self._request(tenant, user, nurse)

        assert check_permission(request, "list_branch") is True

        row.state = "Inactive"
        row.save(update_fields=["state"])

        assert check_permission(request, "list_branch") is False

    def test_it_is_no_profile_to_act_with(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-context")
        user, nurse, row = self._inactive_profile(tenant, "nurse-context")

        assert ResaasContextService.validate_group(user, tenant["branch"], nurse.id) == nurse.id

        row.state = "Inactive"
        row.save(update_fields=["state"])

        with pytest.raises(PermissionDenied):
            ResaasContextService.validate_group(user, tenant["branch"], nurse.id)

    def test_it_is_not_offered_among_the_branch_profiles(self, bootstrap_tenant):
        tenant = bootstrap_tenant("gs-branch")
        user = tenant["user"]
        nurse = _entity_group(tenant)
        BranchUserGroup.objects.create(user=user, group=nurse, branch=tenant["branch"], state="Inactive")

        response = _client(tenant).get(f"/api/django_resaas/branchs/{tenant['branch'].id}/groups/")

        names = [g["name"] for g in response.data]
        assert "Nurse" not in names and "Root" in names


# ------------------------------------------------------------------ data migration

def test_the_migration_activates_every_existing_assignment(bootstrap_tenant):
    tenant = bootstrap_tenant("gs-migration")
    row = BranchUserGroup.objects.create(
        user=_member(tenant), group=_entity_group(tenant), branch=tenant["branch"], state="Inactive",
    )

    migration = importlib.import_module("django_resaas.saas.migrations.0023_branchusergroup_state_active")
    migration.activate_existing(django_apps, None)

    row.refresh_from_db()
    assert row.state == "Active"

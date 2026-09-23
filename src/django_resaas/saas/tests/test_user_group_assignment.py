"""Profile (Group) assignment of a user in the CURRENT Entity/Branch - the
backend behind view_employee's "Profiles" tab (and GroupManagerUser).

The assignment is a BranchUserGroup row; the endpoints are the existing
UserAPIView.userGroups / addGroup / removeGroup, now authenticated,
permission-checked and tenant-scoped. Tenant scope AND permission must both
pass."""
import uuid
from unittest import mock

import pytest
from rest_framework.test import APIClient

from django_resaas.saas.models.branch import Branch
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
    """A user that already belongs to the tenant's Entity."""
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass-12345")
    EntityUser.objects.get_or_create(user=user, entity=tenant["entity"])
    return user


def _entity_group(tenant, name="Nurse"):
    group = Group.objects.create(name=name)
    EntityGroup.objects.create(entity=tenant["entity"], group=group, state="Active")
    return group


def _assign(tenant, user, group, branch=None):
    return BranchUserGroup.objects.create(user=user, group=group, branch=branch or tenant["branch"])


def _client(tenant, **kwargs):
    client = tenant["client"]
    client.raise_request_exception = False
    return client


# ------------------------------------------------------------------ read

class TestListAssigned:

    def test_lists_the_profiles_of_the_user_in_the_current_branch(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-list")
        user = _member(tenant)
        nurse, clerk = _entity_group(tenant, "Nurse"), _entity_group(tenant, "Clerk")
        _assign(tenant, user, nurse)
        _assign(tenant, user, clerk)

        response = _client(tenant).get(_url(user, "userGroups"))

        assert response.status_code == 200
        assert [g["name"] for g in response.data] == ["Clerk", "Nurse"]
        assert {"id", "name", "state"} <= set(response.data[0])

    def test_a_user_without_profiles_gets_an_empty_list(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-empty")

        response = _client(tenant).get(_url(_member(tenant), "userGroups"))

        assert response.status_code == 200 and response.data == []

    def test_only_the_current_entitys_assignments_are_shown(self, bootstrap_tenant):
        mine = bootstrap_tenant("ug-scope-a")
        theirs = bootstrap_tenant("ug-scope-b")
        user = _member(mine)
        EntityUser.objects.get_or_create(user=user, entity=theirs["entity"])
        _assign(mine, user, _entity_group(mine, "Nurse"))
        _assign(theirs, user, _entity_group(theirs, "Administrator"))

        response = _client(mine).get(_url(user, "userGroups"))

        assert [g["name"] for g in response.data] == ["Nurse"]

    def test_only_the_current_branch_is_shown(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-branch")
        user = _member(tenant)
        other_branch = Branch.objects.create(name="Second", entity=tenant["entity"])
        _assign(tenant, user, _entity_group(tenant, "Nurse"))
        _assign(tenant, user, _entity_group(tenant, "Clerk"), branch=other_branch)

        response = _client(tenant).get(_url(user, "userGroups"))

        assert [g["name"] for g in response.data] == ["Nurse"]

    def test_a_user_outside_the_entity_has_nothing_here(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-outsider")
        outsider = User.objects.create_user(username="outsider", email="o@example.com", password="x")

        response = _client(tenant).get(_url(outsider, "userGroups"))

        assert response.status_code == 200 and response.data == []

    def test_is_denied_without_permission_and_when_anonymous(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-list-denied")
        user = _member(tenant)

        with mock.patch(PERMISSION_CHECK, return_value=False):
            denied = _client(tenant).get(_url(user, "userGroups"))
        anonymous = APIClient(raise_request_exception=False).get(_url(user, "userGroups"))

        assert denied.status_code == 403 and denied.data["error"]["code"] == "permission_denied"
        assert anonymous.status_code in (401, 403)

    def test_a_user_can_always_read_their_own_profiles_without_any_permission(self, bootstrap_tenant):
        """The login flow (GroupStore.getGroups) lists the user's own profiles to
        pick one - before any profile, hence any permission, is active."""
        tenant = bootstrap_tenant("ug-self")

        with mock.patch(PERMISSION_CHECK, return_value=False):
            own = _client(tenant).get(_url(tenant["user"], "userGroups"))
            other = _client(tenant).get(_url(_member(tenant), "userGroups"))

        assert own.status_code == 200
        assert tenant["root_group"].id in [g["id"] for g in own.data]
        assert other.status_code == 403

    def test_an_unknown_or_malformed_user_is_a_404(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-404")
        client = _client(tenant)

        assert client.get(f"/api/django_resaas/users/{uuid.uuid4()}/userGroups/").status_code == 404


# ------------------------------------------------------------------ assign

class TestAssign:

    def test_assigns_an_entity_group_in_the_current_branch(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-assign")
        user = _member(tenant)
        nurse = _entity_group(tenant)

        response = _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 200, response.data
        assert BranchUserGroup.objects.filter(user=user, group=nurse, branch=tenant["branch"]).count() == 1
        assert response.data["group"] == str(nurse.id) and response.data["branch"] == str(tenant["branch"].id)

    def test_an_active_duplicate_is_refused_and_creates_nothing(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-duplicate")
        user = _member(tenant)
        nurse = _entity_group(tenant)
        _assign(tenant, user, nurse)

        response = _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 409 and response.data["error"]["code"] == "group_already_assigned"
        assert BranchUserGroup.all_objects.filter(user=user, group=nurse).count() == 1

    def test_a_previously_removed_assignment_is_restored_not_duplicated(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-restore")
        user = _member(tenant)
        nurse = _entity_group(tenant)
        _assign(tenant, user, nurse).delete()

        response = _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 200
        assert BranchUserGroup.all_objects.filter(user=user, group=nurse).count() == 1
        assert BranchUserGroup.objects.filter(user=user, group=nurse).exists()

    def test_a_group_of_another_entity_cannot_be_assigned(self, bootstrap_tenant):
        mine = bootstrap_tenant("ug-cross-a")
        theirs = bootstrap_tenant("ug-cross-b")
        user = _member(mine)
        foreign = _entity_group(theirs, "Foreign")

        response = _client(mine).post(_url(user, "addGroup"), {"group": str(foreign.id)}, format="json")

        assert response.status_code == 404 and response.data["error"]["code"] == "group_not_in_entity"
        assert not BranchUserGroup.objects.filter(user=user, group=foreign).exists()

    def test_a_group_that_no_entity_owns_cannot_be_assigned(self, bootstrap_tenant):
        """e.g. Root: it exists, but it is not one of the Entity's own groups."""
        tenant = bootstrap_tenant("ug-root")
        user = _member(tenant)

        response = _client(tenant).post(_url(user, "addGroup"), {"group": str(tenant["root_group"].id)}, format="json")

        assert response.status_code == 404
        assert not BranchUserGroup.objects.filter(user=user, group=tenant["root_group"]).exists()

    def test_malformed_or_missing_group_ids_are_refused(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-bad-group")
        user = _member(tenant)
        client = _client(tenant)

        assert client.post(_url(user, "addGroup"), {"group": "not-a-uuid"}, format="json").status_code == 404
        assert client.post(_url(user, "addGroup"), {}, format="json").status_code == 404

    def test_the_branch_comes_from_the_context_never_from_the_body(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-branch-body")
        user = _member(tenant)
        nurse = _entity_group(tenant)
        other_branch = Branch.objects.create(name="Elsewhere", entity=tenant["entity"])

        _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id), "branch": str(other_branch.id)}, format="json")

        assert BranchUserGroup.objects.filter(user=user, group=nurse, branch=tenant["branch"]).exists()
        assert not BranchUserGroup.objects.filter(user=user, group=nurse, branch=other_branch).exists()

    def test_a_branch_of_another_entity_cannot_be_targeted_through_the_body(self, bootstrap_tenant):
        mine = bootstrap_tenant("ug-foreign-branch-a")
        theirs = bootstrap_tenant("ug-foreign-branch-b")
        user = _member(mine)
        nurse = _entity_group(mine)

        _client(mine).post(_url(user, "addGroup"), {"group": str(nurse.id), "branch": str(theirs["branch"].id)}, format="json")

        assert not BranchUserGroup.objects.filter(branch=theirs["branch"]).filter(user=user).exists()

    def test_is_denied_without_permission_and_creates_nothing(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-assign-denied")
        user = _member(tenant)
        nurse = _entity_group(tenant)

        with mock.patch(PERMISSION_CHECK, return_value=False):
            response = _client(tenant).post(_url(user, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 403
        assert not BranchUserGroup.objects.filter(user=user, group=nurse).exists()

    def test_a_non_member_is_only_brought_in_with_the_add_entityuser_permission(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-join")
        outsider = User.objects.create_user(username="joiner", email="j@example.com", password="x")
        nurse = _entity_group(tenant)

        only_assignment = lambda request, role: role == "add_branchusergroup"  # noqa: E731
        with mock.patch(PERMISSION_CHECK, side_effect=only_assignment):
            refused = _client(tenant).post(_url(outsider, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert refused.status_code == 403 and refused.data["error"]["code"] == "user_not_in_entity"
        assert not EntityUser.objects.filter(user=outsider, entity=tenant["entity"]).exists()

        allowed = _client(tenant).post(_url(outsider, "addGroup"), {"group": str(nurse.id)}, format="json")

        assert allowed.status_code == 200
        assert EntityUser.objects.filter(user=outsider, entity=tenant["entity"]).exists()
        assert BranchUserGroup.objects.filter(user=outsider, group=nurse, branch=tenant["branch"]).exists()


# ------------------------------------------------------------------ remove

class TestRemove:

    def test_removes_only_the_assignment(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-remove")
        user = _member(tenant)
        nurse = _entity_group(tenant)
        _assign(tenant, user, nurse)

        response = _client(tenant).post(_url(user, "removeGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 200
        assert not BranchUserGroup.objects.filter(user=user, group=nurse).exists()
        # the Group, its EntityGroup, the user and the membership stay
        assert Group.objects.filter(pk=nurse.pk).exists()
        assert EntityGroup.objects.filter(entity=tenant["entity"], group=nurse).exists()
        assert User.objects.filter(pk=user.pk).exists()
        assert EntityUser.objects.filter(user=user, entity=tenant["entity"]).exists()

    def test_the_same_profile_in_another_entity_is_untouched(self, bootstrap_tenant):
        mine = bootstrap_tenant("ug-remove-a")
        theirs = bootstrap_tenant("ug-remove-b")
        user = _member(mine)
        EntityUser.objects.get_or_create(user=user, entity=theirs["entity"])
        shared = Group.objects.create(name="Doctor")
        EntityGroup.objects.create(entity=mine["entity"], group=shared, state="Active")
        EntityGroup.objects.create(entity=theirs["entity"], group=shared, state="Active")
        _assign(mine, user, shared)
        _assign(theirs, user, shared)

        _client(mine).post(_url(user, "removeGroup"), {"group": str(shared.id)}, format="json")

        assert not BranchUserGroup.objects.filter(user=user, group=shared, branch=mine["branch"]).exists()
        assert BranchUserGroup.objects.filter(user=user, group=shared, branch=theirs["branch"]).exists()

    def test_the_same_profile_in_another_branch_is_untouched(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-remove-branch")
        user = _member(tenant)
        nurse = _entity_group(tenant)
        other_branch = Branch.objects.create(name="Second", entity=tenant["entity"])
        _assign(tenant, user, nurse)
        _assign(tenant, user, nurse, branch=other_branch)

        _client(tenant).post(_url(user, "removeGroup"), {"group": str(nurse.id)}, format="json")

        assert BranchUserGroup.objects.filter(user=user, group=nurse, branch=other_branch).exists()

    def test_removing_what_is_not_assigned_is_a_404_not_a_crash(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-remove-none")
        user = _member(tenant)
        nurse = _entity_group(tenant)

        response = _client(tenant).post(_url(user, "removeGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 404 and response.data["error"]["code"] == "group_not_assigned"

    def test_is_denied_without_permission_and_removes_nothing(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-remove-denied")
        user = _member(tenant)
        nurse = _entity_group(tenant)
        _assign(tenant, user, nurse)

        with mock.patch(PERMISSION_CHECK, return_value=False):
            response = _client(tenant).post(_url(user, "removeGroup"), {"group": str(nurse.id)}, format="json")

        assert response.status_code == 403
        assert BranchUserGroup.objects.filter(user=user, group=nurse).exists()

    def test_you_cannot_remove_the_profile_you_are_acting_with(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-remove-self")

        response = _client(tenant).post(
            _url(tenant["user"], "removeGroup"), {"group": str(tenant["root_group"].id)}, format="json"
        )

        assert response.status_code == 400 and response.data["error"]["code"] == "cannot_remove_own_active_group"
        assert BranchUserGroup.objects.filter(user=tenant["user"], group=tenant["root_group"]).exists()

    def test_anonymous_requests_are_refused(self, bootstrap_tenant):
        tenant = bootstrap_tenant("ug-anon")
        user = _member(tenant)

        response = APIClient(raise_request_exception=False).post(_url(user, "removeGroup"), {"group": str(uuid.uuid4())}, format="json")

        assert response.status_code in (401, 403)

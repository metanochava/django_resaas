"""Tenant isolation and per-action authorization of the generic
BranchUserGroup endpoint (/api/django_resaas/branchusergroups/).

A BranchUserGroup row IS an authorization grant (user + group in a branch):
check_permission() resolves effective permissions from it. The endpoint used
to be a plain ModelViewSet that only required authentication: any logged-in
user could list every tenant's assignments, read/change/delete them by id, and
create one - including putting themselves in a group of another Entity, or in
a group their own Entity does not own. These tests pin the fixed contract:

    authenticated + tenant context + permission per action
    + object scope (current Entity + current Branch)
    + relation validation (branch / user / group of the current Entity)

Every negative case also checks the database is unchanged.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_resaas.saas.core.tenant.context import ResaasContextService
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_group import EntityGroup
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db

URL = "/api/django_resaas/branchusergroups/"


def _rows(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


def _entity_group(entity, name):
    group = Group.objects.create(name=name)
    EntityGroup.objects.create(entity=entity, group=group, state="Active")
    return group


def _member(entity, branch, username):
    user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com", password="pass-12345")
    EntityUser.objects.create(entity=entity, user=user, state="Active")
    BranchUser.objects.create(branch=branch, user=user, state="Active")
    return user


def _client(user, entity, branch, group):
    context = ResaasContextService.issue(user=user, entity_id=entity.id, branch_id=branch.id, group_id=group.id)
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return client


@pytest.fixture
def two_tenants(bootstrap_tenant):
    a = bootstrap_tenant("bug-scope-a")
    b = bootstrap_tenant("bug-scope-b")

    a["group"] = _entity_group(a["entity"], "A Billing Clerk")
    b["group"] = _entity_group(b["entity"], "B Billing Clerk")
    a["member"] = _member(a["entity"], a["branch"], "bug-scope-a-member")
    b["member"] = _member(b["entity"], b["branch"], "bug-scope-b-member")

    # one assignment per tenant that is not the caller's own Root grant
    a["row"] = BranchUserGroup.objects.create(branch=a["branch"], user=a["member"], group=a["group"], state="Active")
    b["row"] = BranchUserGroup.objects.create(branch=b["branch"], user=b["member"], group=b["group"], state="Active")
    return a, b


class TestReadScope:
    def test_list_only_shows_current_entity(self, two_tenants):
        a, b = two_tenants

        response = a["client"].get(URL)

        assert response.status_code == 200
        ids = {str(row["id"]) for row in _rows(response)}
        assert str(a["row"].id) in ids
        assert str(b["row"].id) not in ids
        assert all(
            BranchUserGroup.objects.get(pk=row_id).branch_id == a["branch"].id for row_id in ids
        )

    def test_list_does_not_cross_branches_of_same_entity(self, two_tenants):
        a, _ = two_tenants
        other_branch = Branch.objects.create(name="A Second", entity=a["entity"])
        hidden = BranchUserGroup.objects.create(branch=other_branch, user=a["member"], group=a["group"], state="Active")

        ids = {str(row["id"]) for row in _rows(a["client"].get(URL))}

        assert str(hidden.id) not in ids

    def test_retrieve_other_entity_by_id_is_not_found(self, two_tenants):
        a, b = two_tenants

        response = a["client"].get(f"{URL}{b['row'].id}/")

        assert response.status_code == 404


class TestCreateValidation:
    def test_branch_of_another_entity_is_refused(self, two_tenants):
        a, b = two_tenants
        before = BranchUserGroup.objects.count()

        response = a["client"].post(URL, {"branch": b["branch"].id, "user": a["member"].id, "group": a["group"].id})

        assert response.status_code == 400
        assert "branch" in response.json()["error"]["details"]
        assert BranchUserGroup.objects.count() == before

    def test_other_branch_of_same_entity_is_refused(self, two_tenants):
        # cross-branch assignment is not enabled on this endpoint
        a, _ = two_tenants
        other_branch = Branch.objects.create(name="A Other", entity=a["entity"])
        before = BranchUserGroup.objects.count()

        response = a["client"].post(URL, {"branch": other_branch.id, "user": a["member"].id, "group": a["group"].id})

        assert response.status_code == 400
        assert "branch" in response.json()["error"]["details"]
        assert BranchUserGroup.objects.count() == before

    def test_group_of_another_entity_is_refused(self, two_tenants):
        a, b = two_tenants
        before = BranchUserGroup.objects.count()

        response = a["client"].post(URL, {"branch": a["branch"].id, "user": a["member"].id, "group": b["group"].id})

        assert response.status_code == 400
        assert "group" in response.json()["error"]["details"]
        assert BranchUserGroup.objects.count() == before

    def test_group_not_owned_by_any_entity_is_refused(self, two_tenants):
        a, _ = two_tenants
        orphan = Group.objects.create(name="Unowned Group")

        response = a["client"].post(URL, {"branch": a["branch"].id, "user": a["member"].id, "group": orphan.id})

        assert response.status_code == 400
        assert not BranchUserGroup.objects.filter(group=orphan).exists()

    def test_user_of_another_entity_is_refused(self, two_tenants):
        a, b = two_tenants
        before = BranchUserGroup.objects.count()

        response = a["client"].post(URL, {"branch": a["branch"].id, "user": b["member"].id, "group": a["group"].id})

        assert response.status_code == 400
        assert "user" in response.json()["error"]["details"]
        assert BranchUserGroup.objects.count() == before

    def test_legitimate_create_still_works(self, two_tenants):
        a, _ = two_tenants
        other_group = _entity_group(a["entity"], "A Auditor")

        response = a["client"].post(URL, {"branch": a["branch"].id, "user": a["member"].id, "group": other_group.id})

        assert response.status_code == 201
        row = BranchUserGroup.objects.get(branch=a["branch"], user=a["member"], group=other_group)
        assert row.state == "Active"


class TestUpdateScope:
    @pytest.mark.parametrize("field", ["branch", "group", "user"])
    def test_cannot_move_assignment_to_another_entity(self, two_tenants, field):
        a, b = two_tenants
        target = {"branch": b["branch"].id, "group": b["group"].id, "user": b["member"].id}[field]

        response = a["client"].patch(f"{URL}{a['row'].id}/", {field: target}, format="json")

        assert response.status_code == 400
        a["row"].refresh_from_db()
        assert (a["row"].branch_id, a["row"].group_id, a["row"].user_id) == (
            a["branch"].id, a["group"].id, a["member"].id,
        )

    def test_cannot_update_other_entity_row(self, two_tenants):
        a, b = two_tenants

        response = a["client"].patch(f"{URL}{b['row'].id}/", {"group": a["group"].id}, format="json")

        assert response.status_code == 404
        b["row"].refresh_from_db()
        assert b["row"].group_id == b["group"].id

    def test_legitimate_update_still_works(self, two_tenants):
        a, _ = two_tenants
        other_group = _entity_group(a["entity"], "A Cashier")

        response = a["client"].patch(f"{URL}{a['row'].id}/", {"group": other_group.id}, format="json")

        assert response.status_code == 200
        a["row"].refresh_from_db()
        assert a["row"].group_id == other_group.id


class TestDestroyScope:
    def test_cannot_delete_other_entity_row(self, two_tenants):
        a, b = two_tenants

        response = a["client"].delete(f"{URL}{b['row'].id}/")

        assert response.status_code == 404
        assert BranchUserGroup.objects.filter(pk=b["row"].id).exists()

    def test_cannot_delete_own_active_assignment(self, two_tenants):
        a, _ = two_tenants
        own = BranchUserGroup.objects.get(user=a["user"], branch=a["branch"], group=a["root_group"])

        response = a["client"].delete(f"{URL}{own.id}/")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "cannot_remove_own_active_group"
        assert BranchUserGroup.objects.filter(pk=own.id).exists()

    def test_legitimate_delete_still_works(self, two_tenants):
        a, _ = two_tenants

        response = a["client"].delete(f"{URL}{a['row'].id}/")

        assert response.status_code == 204
        assert not BranchUserGroup.objects.filter(pk=a["row"].id).exists()


class TestPermissions:
    @pytest.fixture
    def unprivileged(self, two_tenants):
        """A member of Entity A acting with a group that has no
        branchusergroup permission (it may still pick its own profiles)."""
        a, _ = two_tenants
        client = _client(a["member"], a["entity"], a["branch"], a["group"])
        return a, client

    def test_list_without_permission_is_forbidden(self, unprivileged):
        _, client = unprivileged
        assert client.get(URL).status_code == 403

    def test_retrieve_without_permission_is_forbidden(self, unprivileged):
        a, client = unprivileged
        assert client.get(f"{URL}{a['row'].id}/").status_code == 403

    def test_self_escalation_without_permission_is_forbidden(self, unprivileged):
        # the critical case: granting yourself a more powerful group
        a, client = unprivileged
        before = BranchUserGroup.objects.count()

        response = client.post(URL, {"branch": a["branch"].id, "user": a["member"].id, "group": a["root_group"].id})

        assert response.status_code == 403
        assert BranchUserGroup.objects.count() == before
        assert not BranchUserGroup.objects.filter(user=a["member"], group=a["root_group"]).exists()

    def test_update_without_permission_is_forbidden(self, unprivileged):
        a, client = unprivileged

        response = client.patch(f"{URL}{a['row'].id}/", {"group": a["root_group"].id}, format="json")

        assert response.status_code == 403
        a["row"].refresh_from_db()
        assert a["row"].group_id == a["group"].id

    def test_delete_without_permission_is_forbidden(self, unprivileged):
        a, client = unprivileged
        assert client.delete(f"{URL}{a['row'].id}/").status_code == 403
        assert BranchUserGroup.objects.filter(pk=a["row"].id).exists()

    def test_without_tenant_context_is_forbidden(self, two_tenants):
        a, _ = two_tenants
        client = APIClient()
        client.force_authenticate(user=a["user"])

        assert client.get(URL).status_code == 403

    def test_anonymous_is_unauthorized(self):
        assert APIClient().get(URL).status_code == 401


class TestNoSelfElevation:
    """An Admin (not platform level) holding add_branchusergroup must not give
    ITSELF a profile with permissions its active profile lacks - the same
    delegation rule as editing a profile (group_access_service)."""

    @pytest.fixture
    def admin(self, two_tenants):
        from django.contrib.auth.models import Permission

        a, _ = two_tenants
        # an Entity administrator profile: manages assignments, not platform level
        admin_group = _entity_group(a["entity"], "A Entity Admin")
        admin_group.permissions.add(*Permission.objects.filter(codename__in=(
            "add_branchusergroup", "change_branchusergroup", "list_branchusergroup", "view_branchusergroup",
        )))
        assert not admin_group.permissions.filter(codename="change_entitytype").exists()
        BranchUserGroup.objects.create(user=a["member"], branch=a["branch"], group=admin_group, state="Active")

        powerful = _entity_group(a["entity"], "A Powerful")
        powerful.permissions.add(Permission.objects.get(codename="delete_branch"))
        modest = _entity_group(a["entity"], "A Modest")
        modest.permissions.add(Permission.objects.get(codename="view_branchusergroup"))
        return a, _client(a["member"], a["entity"], a["branch"], admin_group), powerful, modest

    def test_generic_create_refuses_self_grant_of_unheld_permissions(self, admin):
        a, client, powerful, _ = admin

        response = client.post(URL, {"branch": a["branch"].id, "user": a["member"].id, "group": powerful.id})

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_not_held"
        assert not BranchUserGroup.objects.filter(user=a["member"], group=powerful).exists()

    def test_generic_update_refuses_self_grant_of_unheld_permissions(self, admin):
        a, client, powerful, _ = admin
        own = BranchUserGroup.objects.get(user=a["member"], group=a["group"])

        response = client.patch(f"{URL}{own.id}/", {"group": powerful.id}, format="json")

        assert response.status_code == 403
        own.refresh_from_db()
        assert own.group_id == a["group"].id

    def test_add_group_refuses_self_grant_of_unheld_permissions(self, admin):
        a, client, powerful, _ = admin

        response = client.post(f"/api/django_resaas/users/{a['member'].id}/addGroup/", {"group": powerful.id})

        assert response.status_code == 403
        assert not BranchUserGroup.objects.filter(user=a["member"], group=powerful).exists()

    def test_self_grant_of_held_permissions_still_works(self, admin):
        a, client, _, modest = admin

        response = client.post(URL, {"branch": a["branch"].id, "user": a["member"].id, "group": modest.id})

        assert response.status_code == 201

    def test_assigning_another_member_is_unchanged(self, admin):
        a, client, powerful, _ = admin
        other = _member(a["entity"], a["branch"], "bug-scope-a-other")

        response = client.post(URL, {"branch": a["branch"].id, "user": other.id, "group": powerful.id})

        assert response.status_code == 201

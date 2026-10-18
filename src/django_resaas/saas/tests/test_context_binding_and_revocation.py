"""The signed tenant context (X-RESAAS-Context) is not a bearer pass:

- it belongs to the user it was issued for - another authenticated user
  replaying it gets nothing;
- it is re-validated on every request, so removing the membership or the
  profile assignment after it was issued closes access at once (the context
  stays valid for its TTL, the access does not).

ResaasContextService.validate_for_user / validate_entity / validate_branch /
validate_group (core/tenant/context.py)."""
import pytest
from rest_framework.test import APIClient

from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_user import EntityUser

pytestmark = pytest.mark.django_db

URL = "/api/django_resaas/branchusergroups/"


def test_another_users_context_is_refused(bootstrap_tenant):
    a = bootstrap_tenant("ctx-owner")
    b = bootstrap_tenant("ctx-thief")

    thief = APIClient()
    thief.force_authenticate(user=b["user"])
    thief.credentials(HTTP_X_RESAAS_CONTEXT=a["context"]["token"], HTTP_L="1")

    response = thief.get(URL)

    assert response.status_code == 403
    assert list(response.json()) == ["error"]


def test_a_tampered_context_is_refused(bootstrap_tenant):
    a = bootstrap_tenant("ctx-tamper")
    token = a["context"]["token"]
    a["client"].credentials(HTTP_X_RESAAS_CONTEXT=token[:-2] + ("AA" if token[-2:] != "AA" else "BB"), HTTP_L="1")

    assert a["client"].get(URL).status_code == 403


def test_removing_the_profile_assignment_closes_access_with_the_same_context(bootstrap_tenant):
    a = bootstrap_tenant("ctx-revoke-group")
    assert a["client"].get(URL).status_code == 200

    BranchUserGroup.objects.filter(user=a["user"], branch=a["branch"], group=a["root_group"]).delete()

    assert a["client"].get(URL).status_code == 403


def _member_client(tenant, username):
    # an ordinary member: EntityUser + BranchUser + a profile assignment, NOT
    # an Entity admin (admins pass validate_entity/validate_branch by design)
    from django.contrib.auth import get_user_model
    from django_resaas.saas.core.tenant.context import ResaasContextService

    user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com", password="pass-12345")
    EntityUser.objects.create(entity=tenant["entity"], user=user, state="Active")
    BranchUser.objects.create(branch=tenant["branch"], user=user, state="Active")
    BranchUserGroup.objects.create(branch=tenant["branch"], user=user, group=tenant["root_group"], state="Active")
    context = ResaasContextService.issue(user=user, entity_id=tenant["entity"].id, branch_id=tenant["branch"].id, group_id=tenant["root_group"].id)

    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1")
    return user, client


@pytest.mark.parametrize("membership", [EntityUser, BranchUser])
def test_removing_the_membership_closes_access_with_the_same_context(bootstrap_tenant, membership):
    tenant = bootstrap_tenant(f"ctx-revoke-{membership.__name__.lower()}")
    user, client = _member_client(tenant, f"member-{membership.__name__.lower()}")
    assert client.get(URL).status_code == 200

    membership.objects.filter(user=user).delete()

    assert client.get(URL).status_code == 403

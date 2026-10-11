"""UserAPIView.create (django_resaas/users/): everything that can refuse the
request is decided before the User is written. A returned error does not roll
back transaction.atomic(), so the Entity used to be checked after
serializer.save() - a missing Entity context left a User with no Entity."""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.tests.test_permission_api_security import _actor

pytestmark = pytest.mark.django_db

URL = "/api/django_resaas/users/"


def test_without_an_entity_context_nothing_is_created(bootstrap_tenant):
    tenant = bootstrap_tenant("user-create-nocontext")
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user=tenant["user"])  # signed in, no X-RESAAS-Context

    response = client.post(URL, {"username": "orphan"}, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "entity_not_found"
    assert not get_user_model().objects.filter(username="orphan").exists()


def test_with_an_entity_context_the_user_joins_that_entity(bootstrap_tenant):
    tenant = bootstrap_tenant("user-create-ok")

    response = tenant["client"].post(URL, {"username": "joiner"}, format="json")

    assert response.status_code == 201
    new_user = get_user_model().objects.get(username="joiner")
    assert EntityUser.objects.filter(user=new_user, entity=tenant["entity"]).exists()


@override_settings(RESAAS_ENTITLEMENTS={"capacities": {"users": 0}})
def test_over_the_user_capacity_nothing_is_created(bootstrap_tenant):
    tenant = bootstrap_tenant("user-create-full")
    tenant["client"].raise_request_exception = False

    response = tenant["client"].post(URL, {"username": "one-too-many"}, format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "capacity_exceeded"
    assert not get_user_model().objects.filter(username="one-too-many").exists()


def test_invalid_data_creates_nothing_and_answers_the_field_errors(bootstrap_tenant):
    tenant = bootstrap_tenant("user-create-invalid")
    tenant["client"].raise_request_exception = False

    response = tenant["client"].post(URL, {"username": ""}, format="json")

    assert response.status_code == 400
    assert "username" in response.json()["error"]["details"]


# ------------------------------------------------------------------ permissions

def _member(tenant, username):
    user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com", password="x")
    EntityUser.objects.create(user=user, entity=tenant["entity"])
    return user


def test_creating_a_user_needs_add_user(bootstrap_tenant):
    tenant = bootstrap_tenant("user-perm-add")
    denied = _actor(tenant, "user-perm-add-none")
    allowed = _actor(tenant, "user-perm-add-ok", "add_user")

    response = denied.post(URL, {"username": "nope"}, format="json")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert not get_user_model().objects.filter(username="nope").exists()

    assert allowed.post(URL, {"username": "yes"}, format="json").status_code == 201


def test_changing_another_user_needs_change_user_but_not_oneself(bootstrap_tenant):
    tenant = bootstrap_tenant("user-perm-change")
    other = _member(tenant, "user-perm-change-other")
    actor = _actor(tenant, "user-perm-change-actor")
    me = get_user_model().objects.get(username="user-perm-change-actor")

    assert actor.patch(f"{URL}{other.id}/", {"theme": None}, format="json").status_code == 403
    assert actor.patch(f"{URL}{me.id}/", {"theme": None}, format="json").status_code == 200


def test_deleting_a_user_needs_delete_user(bootstrap_tenant):
    tenant = bootstrap_tenant("user-perm-delete")
    other = _member(tenant, "user-perm-delete-other")
    actor = _actor(tenant, "user-perm-delete-actor")

    assert actor.delete(f"{URL}{other.id}/").status_code == 403
    assert get_user_model().objects.filter(pk=other.pk).exists()


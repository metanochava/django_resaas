"""UserAPIView.create (django_resaas/users/): everything that can refuse the
request is decided before the User is written. A returned error does not roll
back transaction.atomic(), so the Entity used to be checked after
serializer.save() - a missing Entity context left a User with no Entity."""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.models.entity_user import EntityUser

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

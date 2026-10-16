"""create_root and the (unrouted) bootstrap TenantAPIView find the platform
Entity the same way group_creator does - the oldest Entity of the SaaS
EntityType - and create it ("Tenant") only on a new installation that has
none."""
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIRequestFactory, force_authenticate

from django_resaas.saas.data.bootstrap.views.bootstrap import TenantAPIView
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType

pytestmark = pytest.mark.django_db

COMMAND = "django_resaas.saas.management.commands.create_root"


@pytest.fixture
def saas_type():
    entity_type, _ = EntityType.objects.get_or_create(name="SaaS", defaults={"state": "Active"})
    Entity.objects.filter(entity_type=entity_type).delete()
    return entity_type


def run_create_root(email, username):
    answers = iter([email, username])
    with mock.patch("builtins.input", lambda *_: next(answers)), \
            mock.patch(f"{COMMAND}.getpass", lambda *_: "S3cret-pass!"), \
            mock.patch(f"{COMMAND}.send_bootstrap_welcome_email", return_value=False), \
            mock.patch(f"{COMMAND}.FrontEndService.load_defaults"), \
            mock.patch(f"{COMMAND}.LanguageService.load_defaults"):
        call_command("create_root")


def test_create_root_on_a_new_installation_creates_the_platform_entity(saas_type):
    run_create_root("root-new@example.com", "root_new")

    entity = Entity.objects.get(entity_type=saas_type)
    assert entity.name == "Tenant"
    assert entity.state == "Active"
    assert Branch.objects.filter(entity=entity, name="Main").exists()


def test_create_root_reuses_the_oldest_entity_of_the_saas_type(saas_type):
    first = Entity.objects.create(name="Platform", entity_type=saas_type)
    Entity.objects.create(name="Second", entity_type=saas_type)

    run_create_root("root-a@example.com", "root_a")
    run_create_root("root-b@example.com", "root_b")   # repeated: nothing new

    assert Entity.objects.filter(entity_type=saas_type).count() == 2
    assert Branch.objects.filter(entity=first, name="Main").count() == 1
    assert set(first.admins.values_list("username", flat=True)) >= {"root_a", "root_b"}


def call_bootstrap(user):
    request = APIRequestFactory().post("/bootstrap/")
    force_authenticate(request, user=user)
    return TenantAPIView.as_view()(request)


def test_bootstrap_view_uses_the_same_platform_entity(saas_type):
    first = Entity.objects.create(name="Platform", entity_type=saas_type)
    user = get_user_model().objects.create_user(
        username="boot_user", email="boot@example.com", password="x-Pass-123"
    )

    response = call_bootstrap(user)
    call_bootstrap(user)   # repeated: nothing new

    assert response.status_code == 201
    assert response.data["data"]["entity"] == "Platform"
    assert response.data["data"]["entity_type"] == "SaaS"
    assert Entity.objects.filter(entity_type=saas_type).count() == 1
    assert Branch.objects.filter(entity=first, name="Main").count() == 1
    assert not EntityType.objects.filter(name="Saas").exclude(pk=saas_type.pk).exists()


def test_bootstrap_view_creates_the_platform_entity_when_none_exists(saas_type):
    user = get_user_model().objects.create_user(
        username="boot_new", email="boot-new@example.com", password="x-Pass-123"
    )

    response = call_bootstrap(user)

    assert response.status_code == 201
    assert Entity.objects.get(entity_type=saas_type).name == "Tenant"


def test_bootstrap_view_does_not_accept_get(saas_type):
    user = get_user_model().objects.create_user(
        username="boot_get", email="boot-get@example.com", password="x-Pass-123"
    )
    request = APIRequestFactory().get("/bootstrap/")
    force_authenticate(request, user=user)

    assert TenantAPIView.as_view()(request).status_code == 405
    assert not Entity.objects.filter(entity_type=saas_type).exists()

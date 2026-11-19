"""admin_profile_service: when a module is activated for an Entity, the Admin
profile gets every permission of that module - never the framework's own
modules (saas, notifications) nor the platform's permissions (Root's)."""
from unittest import mock

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from django_resaas.saas.core.services import admin_profile_service
from django_resaas.saas.models.app import App
from django_resaas.saas.models.entity_app import EntityApp
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.group import Group

pytestmark = pytest.mark.django_db

# an installed module that is not the framework's: django.contrib.auth (label "auth")
MODULE = "django.contrib.auth"


def _admin():
    group, _ = Group.objects.get_or_create(name="Admin")
    return group


def test_admin_gets_every_permission_of_the_module():
    admin = _admin()
    admin.permissions.remove(*Permission.objects.filter(content_type__app_label="auth"))

    added = admin_profile_service.grant_app(MODULE)

    module_perms = set(Permission.objects.filter(content_type__app_label="auth").values_list("id", flat=True))
    assert added == len(module_perms) > 0
    assert module_perms <= set(admin.permissions.values_list("id", flat=True))
    assert admin_profile_service.grant_app(MODULE) == 0           # idempotent


def test_platform_permissions_are_never_granted():
    admin = _admin()
    platform = Permission.objects.create(codename="list_app", name="platform",
                                         content_type=ContentType.objects.get(app_label="auth", model="permission"))

    admin_profile_service.grant_app(MODULE)

    assert not admin.permissions.filter(id=platform.id).exists()


def test_the_framework_modules_are_left_to_the_core_profiles():
    _admin()
    assert admin_profile_service.grant_app("django_resaas.saas") == 0
    assert admin_profile_service.grant_app("not.installed") == 0


def test_activating_a_module_for_an_entity_grants_it(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-grant")
    app = App.objects.create(name="billing")
    EntityTypeApp.objects.create(entity_type=tenant["entity"].entity_type, app=app, state="Active")

    with mock.patch.object(admin_profile_service, "grant_app") as grant:
        response = tenant["client"].post(f"/api/django_resaas/apps/{app.id}/entities/",
                                         {"entity": str(tenant["entity"].id)}, format="json")

    assert response.status_code == 201
    grant.assert_called_once_with("billing")
    assert EntityApp.objects.filter(entity=tenant["entity"], app=app, state="Active").exists()


def test_after_migrate_the_active_modules_get_their_new_permissions(bootstrap_tenant):
    tenant = bootstrap_tenant("admin-migrate")
    app, _ = App.objects.get_or_create(name=MODULE)
    EntityApp.objects.update_or_create(entity=tenant["entity"], app=app, defaults={"state": "Active"})
    config = mock.Mock(label="auth")
    config.name = MODULE

    with mock.patch("django.contrib.auth.management.create_permissions"), \
            mock.patch.object(admin_profile_service, "grant_app") as grant:
        admin_profile_service.on_post_migrate(sender=None, app_config=config)

    grant.assert_called_once_with(MODULE)

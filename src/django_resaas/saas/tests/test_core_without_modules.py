"""The framework runs without any business module: it never names one (HR
used to be activated by default and hardcoded in the core's permissions).
An application chooses its modules (settings.RESAAS_DEFAULT_MODULES) and a
module creates its own permissions (ensure_module_permissions)."""
import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings

from django_resaas.saas.core.services.bootstrap_service import default_modules
from django_resaas.saas.core.signals.permissions import MODULE_PERMISSIONS, ensure_module_permissions
from django_resaas.saas.models.entity_type_app import EntityTypeApp

pytestmark = pytest.mark.django_db


def test_only_the_framework_modules_are_activated_by_default():
    assert default_modules() == ["django_resaas", "notifications"]


@override_settings(RESAAS_DEFAULT_MODULES=["demo"])
def test_the_application_chooses_extra_default_modules():
    assert default_modules() == ["django_resaas", "notifications", "demo"]


@override_settings(RESAAS_DEFAULT_MODULES=["demo"])
def test_a_new_tenant_gets_the_application_default_modules(bootstrap_tenant):
    tenant = bootstrap_tenant("default-modules")

    names = set(EntityTypeApp.objects.filter(entity_type=tenant["entity"].entity_type).values_list("app__name", flat=True))

    assert {"django_resaas", "notifications", "demo"} <= names
    assert "hr" not in names


def test_the_core_names_no_business_module():
    assert set(MODULE_PERMISSIONS) <= {"django_resaas", "notifications"}


def test_a_module_creates_its_own_permissions():
    ensure_module_permissions("demo", [{"codename": "view_demo_dashboard", "name": "Can view Demo dashboard"}])

    assert Permission.objects.filter(codename="view_demo_dashboard", content_type__app_label="demo").exists()


def test_permissions_of_a_module_that_is_not_installed_are_skipped():
    ensure_module_permissions("not_installed", [{"codename": "view_nothing", "name": "x"}])

    assert not Permission.objects.filter(codename="view_nothing").exists()

"""BaseAPIView's module-active guard resolves a view's app_label to the
App-catalogue name before the EntityApp lookup.

The framework's own apps are packaged inside django_resaas and catalogued under
their dotted AppConfig name ("django_resaas.saas", "django_resaas.notifications"),
whose Django label ("django_resaas", "notifications") differs. The guard used to
compare the label against the stored name, so every core BaseAPIView endpoint
(e.g. personcontacts) returned 403 "Module is not active" in deployments that
catalogue modules by name - which production does. Business modules were spared
only because their name == label.
"""
import pytest

from django_resaas.saas.models.entity_app import EntityApp

pytestmark = pytest.mark.django_db

CORE = "/api/django_resaas/personcontacts/"


def test_bootstrap_seeds_the_core_app_by_its_catalogue_name(bootstrap_tenant):
    tenant = bootstrap_tenant("fw-guard-seed")
    # default_modules() activates the framework apps by their AppConfig.name
    assert EntityApp.objects.filter(
        entity=tenant["entity"], app__name="django_resaas.saas", state="Active"
    ).exists()


def test_core_endpoint_is_active_when_catalogued_by_dotted_name(bootstrap_tenant):
    tenant = bootstrap_tenant("fw-guard-active")
    assert tenant["client"].get(CORE).status_code == 200


def test_core_endpoint_denied_when_the_core_app_is_absent(bootstrap_tenant):
    tenant = bootstrap_tenant("fw-guard-absent")
    EntityApp.objects.filter(entity=tenant["entity"]).delete()

    response = tenant["client"].get(CORE)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"

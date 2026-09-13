"""AppSchemaAPIView.destroy() only protected the exact names
"django_resaas"/"hr" - any other "django_resaas.<something>" entry
(django_resaas.saas, django_resaas.hr, django_resaas.notifications,
...) was NOT protected by name, even though every one of them is core
platform code, not a scaffolded business module. Fixed: any name equal
to "django_resaas" or starting with "django_resaas." is protected,
checked before the on-disk existence check (so "protected" is the
answer even for a name with no folder of its own inside BASE_DIR - the
dotted ones live inside the library package, not as a scaffolded
top-level folder).

Note: a name with a dot (django_resaas.saas, django_resaas.
notifications, ...) can never actually reach destroy() over HTTP in
the first place - same routing constraint documented in
test_app_schema_dotted_apps.py for retrieve()/GET (DRF/Django treats
"." in a path segment as a format-suffix separator, never part of the
pk). The protection check in destroy() is still correct/defensive for
whichever name DOES reach it (the bare "django_resaas", or any future
caller that resolves pk differently) - the practical UI-level
protection for dotted names is the Delete button itself being disabled
for any django_resaas-prefixed module (see pages/commands/
AppCreatePage.vue)."""
import pytest
from django.contrib.auth.models import Permission

pytestmark = pytest.mark.django_db


def _grant_delete_app(tenant):
    tenant["root_group"].permissions.add(Permission.objects.get(codename="delete_app"))


class TestDjangoResaasPrefixIsProtected:

    def test_bare_django_resaas_is_protected(self, bootstrap_tenant, settings):
        settings.DEBUG = True
        tenant = bootstrap_tenant("app-protected-bare")
        _grant_delete_app(tenant)
        client = tenant["client"]

        response = client.delete("/api/django_resaas/resaasapps/django_resaas/")

        assert response.status_code == 200, response.data
        assert response.data.get("alert_warning")

    def test_dotted_names_can_never_reach_destroy(self, bootstrap_tenant, settings):
        """Documents the routing constraint (see module docstring) -
        this is exactly why the Delete button itself must stay
        disabled for django_resaas-prefixed modules in the UI."""
        settings.DEBUG = True
        tenant = bootstrap_tenant("app-protected-dotted-404")
        _grant_delete_app(tenant)
        client = tenant["client"]

        response = client.delete("/api/django_resaas/resaasapps/django_resaas.notifications/")

        assert response.status_code == 404

    def test_unrelated_module_name_is_not_protected(self, bootstrap_tenant, settings):
        """Backward compatible: a genuinely unknown/unrelated module
        name must still fall through to the normal not_found path, not
        get swept up by an overly broad prefix check."""
        settings.DEBUG = True
        tenant = bootstrap_tenant("app-not-protected")
        _grant_delete_app(tenant)
        client = tenant["client"]

        response = client.delete("/api/django_resaas/resaasapps/totally_unrelated_module/")

        assert response.status_code == 400

"""AppSchemaAPIView.list()/.retrieve()/.lookup() used to (or, for
retrieve/lookup, would) compare a MY_APPS entry directly against
`model._meta.app_label` - correct for a flat entry like "saude", but
silently wrong for a dotted AppConfig import path like "django_resaas.
saas" (real app_label "django_resaas", see saas/apps.py's `label =
"django_resaas"`) or "django_resaas.hr" (label "hr") - every such
entry always showed 0 models / an empty model list, even though the
app is very much installed and has real models.

Fixed via `_resolve_app_label()` (management/apicommands/view/
app_schema.py), which resolves a MY_APPS entry to its real app_label
through Django's own AppConfig registry before comparing.

`retrieve()` itself (GET resaasapps/<pk>/) can never actually receive
a dotted pk over HTTP - DRF/Django's router treats any "." in a path
segment as a format-suffix separator ("django_resaas.saas/" resolves
to pk="django_resaas", format="saas", not the full dotted string) -
confirmed by `test_retrieve_can_never_receive_a_dotted_pk` below. The
new `lookup()` action (GET resaasapps/lookup/?app=<name>) takes the
name as a query param instead, sidestepping that entirely - it is what
the frontend now uses for every module lookup, dotted or not."""
import pytest

pytestmark = pytest.mark.django_db


class TestRetrieveResolvesDottedAppPath:

    def test_retrieve_can_never_receive_a_dotted_pk(self, bootstrap_tenant):
        """Documents the actual routing constraint (see module
        docstring) - not a bug in this view, a property of how DRF/
        Django route path segments. This is exactly why lookup()
        exists."""
        tenant = bootstrap_tenant("app-schema-dotted-retrieve-404")
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/django_resaas.saas/")

        assert response.status_code == 404

    def test_retrieve_with_real_label_still_works(self, bootstrap_tenant):
        """Backward compatible: an entry that already IS the real
        app_label (no dot) must keep working exactly as before."""
        tenant = bootstrap_tenant("app-schema-plain-retrieve")
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/django_resaas/")

        assert response.status_code == 200, response.data
        assert "Entity" in response.data["models"]


class TestLookupResolvesDottedAppPath:

    def test_lookup_with_dotted_saas_path_lists_real_models(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-schema-dotted-lookup")
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/lookup/?app=django_resaas.saas")

        assert response.status_code == 200, response.data
        assert "Entity" in response.data["models"]
        assert "EntityType" in response.data["models"]

    def test_lookup_with_dotted_hr_path_lists_real_models(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-schema-dotted-lookup-hr", modules=("hr",))
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/lookup/?app=django_resaas.hr")

        assert response.status_code == 200, response.data
        assert "Employee" in response.data["models"]

    def test_lookup_with_plain_label_still_works(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-schema-plain-lookup")
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/lookup/?app=django_resaas")

        assert response.status_code == 200, response.data
        assert "Entity" in response.data["models"]

    def test_lookup_with_unknown_app_returns_empty_models(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-schema-lookup-unknown")
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/lookup/?app=nope")

        assert response.status_code == 200, response.data
        assert response.data["models"] == []


class TestListResolvesDottedAppPath:

    def test_list_counts_models_for_dotted_entries(self, bootstrap_tenant, settings):
        settings.DEBUG = True
        settings.MY_APPS = ["django_resaas.saas"]

        tenant = bootstrap_tenant("app-schema-dotted-list")
        client = tenant["client"]

        response = client.get("/api/django_resaas/resaasapps/")

        assert response.status_code == 200, response.data
        entry = next(a for a in response.data["apps"] if a["name"] == "django_resaas.saas")

        # Antes do fix: sempre 0 (a comparação nunca batia certo).
        assert entry["models"] > 0

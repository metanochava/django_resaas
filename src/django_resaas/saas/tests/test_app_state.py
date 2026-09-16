"""AppSerializer exposes App.state (TimeModel's Active/Inactive field,
already set on registration by bootstrap_service.py/app_service.py/
create_root.py) and AppAPIView (a plain ModelViewSet) lets it be
PATCHed - the activate/deactivate button on AppCreatePage.vue's module
cards reads/writes through exactly this, no new endpoint."""
import pytest

from django_resaas.saas.models.app import App

pytestmark = pytest.mark.django_db


class TestAppState:

    def test_list_includes_state(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-state-list")
        client = tenant["client"]

        App.objects.create(name="billing", state="Active")

        response = client.get("/api/django_resaas/apps/", {"page_size": 0})

        assert response.status_code == 200
        row = next(r for r in response.data["results"] if r["name"] == "billing")
        # BaseSerializer represents a choice field as {id,value,label}
        # on read (same convention as Branch.state elsewhere)
        assert row["state"]["value"] == "Active"

    def test_detail_includes_state(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-state-detail")
        client = tenant["client"]

        app = App.objects.create(name="billing", state="Inactive")

        response = client.get(f"/api/django_resaas/apps/{app.id}/")

        assert response.status_code == 200
        assert response.data["state"]["value"] == "Inactive"

    def test_patch_activates_app(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-state-activate")
        client = tenant["client"]

        app = App.objects.create(name="billing", state="Inactive")

        response = client.patch(
            f"/api/django_resaas/apps/{app.id}/",
            {"state": "Active"},
            content_type="application/json",
        )

        assert response.status_code == 200
        app.refresh_from_db()
        assert app.state == "Active"

    def test_patch_deactivates_app(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-state-deactivate")
        client = tenant["client"]

        app = App.objects.create(name="billing", state="Active")

        response = client.patch(
            f"/api/django_resaas/apps/{app.id}/",
            {"state": "Inactive"},
            content_type="application/json",
        )

        assert response.status_code == 200
        app.refresh_from_db()
        assert app.state == "Inactive"

    def test_patch_rejects_an_invalid_state_value(self, bootstrap_tenant):
        tenant = bootstrap_tenant("app-state-invalid")
        client = tenant["client"]

        app = App.objects.create(name="billing", state="Active")

        response = client.patch(
            f"/api/django_resaas/apps/{app.id}/",
            {"state": "Suspended"},
            content_type="application/json",
        )

        assert response.status_code == 400
        app.refresh_from_db()
        assert app.state == "Active"

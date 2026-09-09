"""Personalização de header/footer (cor/gradiente/imagem/transparente
+ cor de texto), cascata User > Entity > EntityType > default -
engine/core/services/interface_config_service.py +
engine/models/mixins/visual_area.py + os endpoints
update_interface/reset_interface em UserAPIView.
"""
import pytest

from django_resaas.engine.core.services.interface_config_service import (
    DEFAULT_CONFIG,
    InterfaceConfigService,
)
from django_resaas.engine.models.user_theme_override import UserThemeOverride

pytestmark = pytest.mark.django_db


class TestResolutionCascade:

    def test_default_when_nothing_is_set(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-default")

        config = InterfaceConfigService.resolve(
            user=tenant["user"], entity=tenant["entity"], entity_type=tenant["entity_type"]
        )

        assert config == DEFAULT_CONFIG

    def test_entity_type_level_is_used_when_entity_has_nothing(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-type")

        tenant["entity_type"].header_background_type = "color"
        tenant["entity_type"].header_background_color = "#00ff00"
        tenant["entity_type"].save()

        config = InterfaceConfigService.resolve_area(
            "header", user=tenant["user"], entity=tenant["entity"], entity_type=tenant["entity_type"]
        )

        assert config["background"] == {"type": "color", "value": "#00ff00"}

    def test_entity_overrides_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-entity")

        tenant["entity_type"].header_background_type = "color"
        tenant["entity_type"].header_background_color = "#00ff00"
        tenant["entity_type"].save()

        tenant["entity"].header_background_type = "color"
        tenant["entity"].header_background_color = "#ff0000"
        tenant["entity"].save()

        config = InterfaceConfigService.resolve_area(
            "header", user=tenant["user"], entity=tenant["entity"], entity_type=tenant["entity_type"]
        )

        assert config["background"] == {"type": "color", "value": "#ff0000"}

    def test_user_override_wins_over_entity(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-user")

        tenant["entity"].header_background_type = "color"
        tenant["entity"].header_background_color = "#ff0000"
        tenant["entity"].save()

        UserThemeOverride.objects.create(
            user=tenant["user"],
            header_background_type="color",
            header_background_color="#0000ff",
        )

        config = InterfaceConfigService.resolve_area(
            "header", user=tenant["user"], entity=tenant["entity"], entity_type=tenant["entity_type"]
        )

        assert config["background"] == {"type": "color", "value": "#0000ff"}

    def test_transparent_needs_no_value(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-transparent")

        tenant["entity"].footer_background_type = "transparent"
        tenant["entity"].save()

        config = InterfaceConfigService.resolve_area(
            "footer", user=tenant["user"], entity=tenant["entity"], entity_type=tenant["entity_type"]
        )

        assert config["background"] == {"type": "transparent", "value": None}

    def test_gradient_without_value_does_not_count_as_configured(self, bootstrap_tenant):
        """type='gradient' mas sem gradient definido não deve "vencer"
        silenciosamente com um valor vazio - cai para o próximo nível."""
        tenant = bootstrap_tenant("iface-empty-gradient")

        tenant["entity"].header_background_type = "gradient"
        tenant["entity"].header_background_gradient = None
        tenant["entity"].save()

        tenant["entity_type"].header_background_type = "color"
        tenant["entity_type"].header_background_color = "#123456"
        tenant["entity_type"].save()

        config = InterfaceConfigService.resolve_area(
            "header", user=tenant["user"], entity=tenant["entity"], entity_type=tenant["entity_type"]
        )

        assert config["background"] == {"type": "color", "value": "#123456"}

    def test_resolve_override_only_is_none_without_customization(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-no-override")

        result = InterfaceConfigService.resolve_override_only(user=tenant["user"])

        assert result == {"header": None, "footer": None}


class TestInterfaceEndpoints:

    def test_me_returns_resolved_interface_config(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-me")

        response = tenant["client"].get("/me/")

        assert response.status_code == 200, response.data
        assert response.data["interface_config"] == DEFAULT_CONFIG
        assert response.data["interface_override"] == {"header": None, "footer": None}

    def test_update_interface_creates_override_and_reflects_in_me(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-update")

        response = tenant["client"].post(
            "/api/django_resaas/users/update_interface/",
            {"area": "header", "background_type": "color", "background_color": "#abcdef", "text_color": "#111111"},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["interface_config"]["header"]["background"] == {
            "type": "color", "value": "#abcdef",
        }
        assert response.data["interface_config"]["header"]["text_color"] == "#111111"
        # footer nunca foi tocado - continua no default.
        assert response.data["interface_config"]["footer"] == DEFAULT_CONFIG["footer"]

        me_response = tenant["client"].get("/me/")
        assert me_response.data["interface_config"]["header"]["background"]["value"] == "#abcdef"

    def test_update_interface_rejects_unknown_area(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-badarea")

        response = tenant["client"].post(
            "/api/django_resaas/users/update_interface/",
            {"area": "sidebar", "background_type": "color"},
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_reset_interface_clears_only_the_requested_area(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-reset")

        tenant["client"].post(
            "/api/django_resaas/users/update_interface/",
            {"area": "header", "background_type": "color", "background_color": "#abcdef"},
            content_type="application/json",
        )
        tenant["client"].post(
            "/api/django_resaas/users/update_interface/",
            {"area": "footer", "background_type": "color", "background_color": "#123456"},
            content_type="application/json",
        )

        response = tenant["client"].post(
            "/api/django_resaas/users/reset_interface/",
            {"area": "header"},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["interface_override"]["header"] is None
        assert response.data["interface_override"]["footer"] is not None

    def test_reset_interface_without_area_clears_both(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-reset-all")

        tenant["client"].post(
            "/api/django_resaas/users/update_interface/",
            {"area": "header", "background_type": "color", "background_color": "#abcdef"},
            content_type="application/json",
        )

        response = tenant["client"].post(
            "/api/django_resaas/users/reset_interface/",
            {},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["interface_override"] == {"header": None, "footer": None}

    def test_reset_without_prior_override_is_a_safe_noop(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-reset-noop")

        response = tenant["client"].post(
            "/api/django_resaas/users/reset_interface/",
            {},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["interface_override"] == {"header": None, "footer": None}

    def test_each_user_has_an_independent_override(self, bootstrap_tenant):
        tenant_a = bootstrap_tenant("iface-a")
        tenant_b = bootstrap_tenant("iface-b")

        tenant_a["client"].post(
            "/api/django_resaas/users/update_interface/",
            {"area": "header", "background_type": "color", "background_color": "#abcdef"},
            content_type="application/json",
        )

        response_b = tenant_b["client"].get("/me/")

        assert response_b.data["interface_override"]["header"] is None

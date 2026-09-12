"""Personalização de header/footer (cor/gradiente/imagem/transparente
+ cor de texto), cascata Entity > EntityType > default -
saas/core/services/interface_config_service.py +
saas/models/mixins/visual_area.py.

Já não existe um nível de personalização por-utilizador aqui (o antigo
UserThemeOverride + update_interface/reset_interface foram removidos -
ver test_user_theme_resolution.py para a personalização actual do User
via theme/layout_settings/typography/animation_settings + ThemeSurface).
"""
import pytest

from django_resaas.saas.core.services.interface_config_service import (
    DEFAULT_CONFIG,
    InterfaceConfigService,
)

pytestmark = pytest.mark.django_db


class TestResolutionCascade:

    def test_default_when_nothing_is_set(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-default")

        config = InterfaceConfigService.resolve(
            entity=tenant["entity"], entity_type=tenant["entity"].entity_type
        )

        assert config == DEFAULT_CONFIG

    def test_entity_type_level_is_used_when_entity_has_nothing(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-type")

        tenant["entity"].entity_type.header_background_type = "color"
        tenant["entity"].entity_type.header_background_color = "#00ff00"
        tenant["entity"].entity_type.save()

        config = InterfaceConfigService.resolve_area(
            "header", entity=tenant["entity"], entity_type=tenant["entity"].entity_type
        )

        assert config["background"] == {"type": "color", "value": "#00ff00"}

    def test_entity_overrides_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-entity")

        tenant["entity"].entity_type.header_background_type = "color"
        tenant["entity"].entity_type.header_background_color = "#00ff00"
        tenant["entity"].entity_type.save()

        tenant["entity"].header_background_type = "color"
        tenant["entity"].header_background_color = "#ff0000"
        tenant["entity"].save()

        config = InterfaceConfigService.resolve_area(
            "header", entity=tenant["entity"], entity_type=tenant["entity"].entity_type
        )

        assert config["background"] == {"type": "color", "value": "#ff0000"}

    def test_transparent_needs_no_value(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-transparent")

        tenant["entity"].footer_background_type = "transparent"
        tenant["entity"].save()

        config = InterfaceConfigService.resolve_area(
            "footer", entity=tenant["entity"], entity_type=tenant["entity"].entity_type
        )

        assert config["background"] == {"type": "transparent", "value": None}

    def test_gradient_without_value_does_not_count_as_configured(self, bootstrap_tenant):
        """type='gradient' mas sem gradient definido não deve "vencer"
        silenciosamente com um valor vazio - cai para o próximo nível."""
        tenant = bootstrap_tenant("iface-empty-gradient")

        tenant["entity"].header_background_type = "gradient"
        tenant["entity"].header_background_gradient = None
        tenant["entity"].save()

        tenant["entity"].entity_type.header_background_type = "color"
        tenant["entity"].entity_type.header_background_color = "#123456"
        tenant["entity"].entity_type.save()

        config = InterfaceConfigService.resolve_area(
            "header", entity=tenant["entity"], entity_type=tenant["entity"].entity_type
        )

        assert config["background"] == {"type": "color", "value": "#123456"}


class TestInterfaceEndpoints:

    def test_me_returns_resolved_interface_config(self, bootstrap_tenant):
        tenant = bootstrap_tenant("iface-me")

        response = tenant["client"].get("/api/me/")

        assert response.status_code == 200, response.data
        assert response.data["interface_config"] == DEFAULT_CONFIG
        assert "interface_override" not in response.data

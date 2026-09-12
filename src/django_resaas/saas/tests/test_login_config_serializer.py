"""EntitySerializer/EntityTypeSerializer's login_config/login_background
- regressão: os campos login_background_type/color/gradient/image e
login_position deixaram de existir directamente em Entity/EntityType
(ver CLAUDE.md do quasar_resaas, secção 21: "posição = LayoutSetting,
aparência = ThemeSurface"), mas get_login_background()/get_login_config()
continuavam a acedê-los directamente - rebentava com AttributeError em
qualquer listagem de EntityType/Entity (500 em produção).
"""
import pytest

from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.theme_surface import ThemeSurface

pytestmark = pytest.mark.django_db


class TestLoginConfigSerializer:

    def test_entitytype_list_does_not_crash_without_theme(self, bootstrap_tenant):
        tenant = bootstrap_tenant("login-cfg-type-empty")

        response = tenant["client"].get(
            "/api/django_resaas/entitytypes/?objects=alive"
        )

        assert response.status_code == 200, response.data

    def test_entity_list_does_not_crash_without_theme(self, bootstrap_tenant):
        tenant = bootstrap_tenant("login-cfg-entity-empty")

        response = tenant["client"].get("/api/django_resaas/entitys/")

        assert response.status_code == 200, response.data

    def test_entity_login_config_resolves_from_theme_surface(self, bootstrap_tenant):
        tenant = bootstrap_tenant("login-cfg-entity-surface")
        entity = tenant["entity"]

        theme = Theme.objects.create(name="LoginTheme", state="Active")
        ThemeSurface.objects.create(
            theme=theme,
            area="login",
            background_type="color",
            background_color="#123456",
        )

        layout = LayoutSetting.objects.create(
            name="LoginLayout", state="Active", login_position="bottom-right"
        )

        entity.theme = theme
        entity.layout_settings = layout
        entity.save()

        response = tenant["client"].get(
            f"/api/django_resaas/entitys/{entity.id}/"
        )

        assert response.status_code == 200, response.data
        assert response.data["login_config"]["position"] == "bottom-right"
        assert response.data["login_config"]["background"] == {
            "type": "color", "value": "#123456",
        }

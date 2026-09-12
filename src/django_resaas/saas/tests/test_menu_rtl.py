"""menu_rtl - UserAPIView.toggle_menu_rtl().

menu_rtl vive exclusivamente em
django_resaas.saas.models.layout_setting.LayoutSetting, resolvido via
User.get_effective_layout()/get_ui_config()/get_ui_sources()
(User > Entity > EntityType). Não existe UserThemeOverride nem outro
campo paralelo (rtl_menu, menu_direction, is_rtl, ...).
"""
import pytest

from django_resaas.saas.models.layout_setting import LayoutSetting

pytestmark = pytest.mark.django_db


def _make_layout(name, **kwargs):
    return LayoutSetting.objects.create(name=name, state="Active", **kwargs)


class TestMenuRtlResolution:

    def test_defaults_to_false_when_nothing_configured(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-default")
        user = tenant["user"]
        entity = tenant["entity"]

        assert user.get_effective_layout(entity) is None
        assert user.get_ui_sources(entity)["layout"] is None

    def test_entity_type_level_layout_is_used(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-type")
        user = tenant["user"]
        entity = tenant["entity"]

        layout = _make_layout("Type layout", menu_rtl=True)
        entity.entity_type.layout_settings = layout
        entity.entity_type.save()

        assert user.get_effective_layout(entity).menu_rtl is True
        assert user.get_ui_sources(entity)["layout"] == "entity_type"

    def test_entity_overrides_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-entity")
        user = tenant["user"]
        entity = tenant["entity"]

        entity.entity_type.layout_settings = _make_layout("Type layout", menu_rtl=True)
        entity.entity_type.save()

        entity.layout_settings = _make_layout("Entity layout", menu_rtl=False)
        entity.save()

        assert user.get_effective_layout(entity).menu_rtl is False
        assert user.get_ui_sources(entity)["layout"] == "entity"

    def test_user_overrides_entity(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-user")
        user = tenant["user"]
        entity = tenant["entity"]

        entity.layout_settings = _make_layout("Entity layout", menu_rtl=False)
        entity.save()

        user.layout_settings = _make_layout("User layout", menu_rtl=True)
        user.save()

        assert user.get_effective_layout(entity).menu_rtl is True
        assert user.get_ui_sources(entity)["layout"] == "user"


class TestToggleMenuRtlEndpoint:

    def test_toggle_creates_a_personal_copy_preserving_other_fields(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-toggle-new")
        user = tenant["user"]
        entity = tenant["entity"]

        entity.layout_settings = _make_layout(
            "Entity layout", menu_rtl=False, sidebar_width=321,
        )
        entity.save()

        assert user.layout_settings is None

        response = tenant["client"].post(
            "/api/django_resaas/users/toggle_menu_rtl/", {},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["ui_config"]["layout"]["menu_rtl"] is True
        assert response.data["ui_sources"]["layout"] == "user"

        user.refresh_from_db()
        assert user.layout_settings is not None
        assert user.layout_settings.menu_rtl is True
        # preservou o resto da configuração herdada, não voltou aos
        # defaults do modelo.
        assert user.layout_settings.sidebar_width == 321

    def test_toggle_flips_an_existing_personal_override_in_place(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-toggle-existing")
        user = tenant["user"]

        own_layout = _make_layout("User layout", menu_rtl=False)
        user.layout_settings = own_layout
        user.save()

        response = tenant["client"].post(
            "/api/django_resaas/users/toggle_menu_rtl/", {},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["ui_config"]["layout"]["menu_rtl"] is True

        own_layout.refresh_from_db()
        assert own_layout.menu_rtl is True

        user.refresh_from_db()
        # continua a ser o MESMO LayoutSetting (só o campo mudou).
        assert user.layout_settings_id == own_layout.id

    def test_toggle_twice_returns_to_the_original_value(self, bootstrap_tenant):
        tenant = bootstrap_tenant("menu-rtl-toggle-twice")

        first = tenant["client"].post(
            "/api/django_resaas/users/toggle_menu_rtl/", {},
            content_type="application/json",
        )
        second = tenant["client"].post(
            "/api/django_resaas/users/toggle_menu_rtl/", {},
            content_type="application/json",
        )

        assert first.data["ui_config"]["layout"]["menu_rtl"] is True
        assert second.data["ui_config"]["layout"]["menu_rtl"] is False

"""sidebar_mini - UserAPIView.toggle_sidebar_mini().

sidebar_mini vive exclusivamente em
django_resaas.saas.models.layout_setting.LayoutSetting, resolvido via
User.get_effective_layout()/get_ui_config()/get_ui_sources() (User >
Entity > EntityType) - exactly the same resolution/toggle mechanism
already covered for menu_rtl in test_menu_rtl.py (both share
UserAPIView._toggle_personal_layout_field()).
"""
import pytest

from django_resaas.saas.models.layout_setting import LayoutSetting

pytestmark = pytest.mark.django_db


def _make_layout(name, **kwargs):
    return LayoutSetting.objects.create(name=name, state="Active", **kwargs)


class TestToggleSidebarMiniEndpoint:

    def test_toggle_creates_a_personal_copy_preserving_other_fields(self, bootstrap_tenant):
        tenant = bootstrap_tenant("sidebar-mini-toggle-new")
        user = tenant["user"]
        entity = tenant["entity"]

        entity.layout_settings = _make_layout(
            "Entity layout", sidebar_mini=False, sidebar_width=321,
        )
        entity.save()

        assert user.layout_settings is None

        response = tenant["client"].post(
            "/api/django_resaas/users/toggle_sidebar_mini/", {},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["ui_config"]["layout"]["sidebar"]["mini"] is True
        assert response.data["ui_sources"]["layout"] == "user"

        user.refresh_from_db()
        assert user.layout_settings is not None
        assert user.layout_settings.sidebar_mini is True
        # preservou o resto da configuração herdada, não voltou aos
        # defaults do modelo.
        assert user.layout_settings.sidebar_width == 321

    def test_toggle_flips_an_existing_personal_override_in_place(self, bootstrap_tenant):
        tenant = bootstrap_tenant("sidebar-mini-toggle-existing")
        user = tenant["user"]

        own_layout = _make_layout("User layout", sidebar_mini=False)
        user.layout_settings = own_layout
        user.save()

        response = tenant["client"].post(
            "/api/django_resaas/users/toggle_sidebar_mini/", {},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data
        assert response.data["ui_config"]["layout"]["sidebar"]["mini"] is True

        own_layout.refresh_from_db()
        assert own_layout.sidebar_mini is True

        user.refresh_from_db()
        # continua a ser o MESMO LayoutSetting (só o campo mudou).
        assert user.layout_settings_id == own_layout.id

    def test_toggle_twice_returns_to_the_original_value(self, bootstrap_tenant):
        tenant = bootstrap_tenant("sidebar-mini-toggle-twice")

        first = tenant["client"].post(
            "/api/django_resaas/users/toggle_sidebar_mini/", {},
            content_type="application/json",
        )
        second = tenant["client"].post(
            "/api/django_resaas/users/toggle_sidebar_mini/", {},
            content_type="application/json",
        )

        assert first.data["ui_config"]["layout"]["sidebar"]["mini"] is True
        assert second.data["ui_config"]["layout"]["sidebar"]["mini"] is False

    def test_toggling_sidebar_mini_does_not_touch_menu_rtl(self, bootstrap_tenant):
        """Regression: both actions share _toggle_personal_layout_field()
        - confirms the shared helper only ever mutates the ONE field it
        was called for, never the other boolean it also knows about."""
        tenant = bootstrap_tenant("sidebar-mini-independent")
        user = tenant["user"]
        entity = tenant["entity"]

        entity.layout_settings = _make_layout(
            "Entity layout", menu_rtl=True, sidebar_mini=False,
        )
        entity.save()

        response = tenant["client"].post(
            "/api/django_resaas/users/toggle_sidebar_mini/", {},
            content_type="application/json",
        )

        assert response.data["ui_config"]["layout"]["sidebar"]["mini"] is True
        assert response.data["ui_config"]["layout"]["menu_rtl"] is True

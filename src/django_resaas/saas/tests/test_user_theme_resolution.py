"""Resolução de aparência User > Entity > EntityType via os FKs
directos em django_resaas.saas.models.user.User
(theme/layout_settings/typography/animation_settings) -
User.get_ui_config()/get_ui_sources().

Substitui a antiga arquitectura UserThemeOverride (removida): já não
existe um objecto de override próprio - `user.theme is None` significa
"herdar da Entity", tal como `entity.theme is None` significa "herdar
da EntityType".
"""
import pytest

from django_resaas.saas.models.theme import Theme

pytestmark = pytest.mark.django_db


def _make_theme(name):
    return Theme.objects.create(name=name, state="Active")


class TestThemeResolutionCascade:

    def test_entity_type_wins_when_nothing_else_is_set(self, bootstrap_tenant):
        tenant = bootstrap_tenant("theme-case1")
        entity = tenant["entity"]
        user = tenant["user"]

        theme_a = _make_theme("A")
        entity.entity_type.theme = theme_a
        entity.entity_type.save()

        assert user.get_effective_theme(entity) == theme_a
        assert user.get_ui_sources(entity)["theme"] == "entity_type"

    def test_entity_overrides_entity_type(self, bootstrap_tenant):
        tenant = bootstrap_tenant("theme-case2")
        entity = tenant["entity"]
        user = tenant["user"]

        theme_a = _make_theme("A")
        theme_b = _make_theme("B")

        entity.entity_type.theme = theme_a
        entity.entity_type.save()

        entity.theme = theme_b
        entity.save()

        assert user.get_effective_theme(entity) == theme_b
        assert user.get_ui_sources(entity)["theme"] == "entity"

    def test_user_overrides_entity(self, bootstrap_tenant):
        tenant = bootstrap_tenant("theme-case3")
        entity = tenant["entity"]
        user = tenant["user"]

        theme_a = _make_theme("A")
        theme_b = _make_theme("B")
        theme_c = _make_theme("C")

        entity.entity_type.theme = theme_a
        entity.entity_type.save()

        entity.theme = theme_b
        entity.save()

        user.theme = theme_c
        user.save()

        assert user.get_effective_theme(entity) == theme_c
        assert user.get_ui_sources(entity)["theme"] == "user"

    def test_clearing_user_override_falls_back_to_entity(self, bootstrap_tenant):
        """user.theme = None não é "sem tema" - é "voltar a herdar",
        sem precisar de nenhum objecto adicional (não há UserThemeOverride
        para apagar)."""
        tenant = bootstrap_tenant("theme-case4")
        entity = tenant["entity"]
        user = tenant["user"]

        theme_b = _make_theme("B")
        theme_c = _make_theme("C")

        entity.theme = theme_b
        entity.save()

        user.theme = theme_c
        user.save()

        assert user.get_effective_theme(entity) == theme_c

        user.theme = None
        user.save()

        assert user.get_effective_theme(entity) == theme_b
        assert user.get_ui_sources(entity)["theme"] == "entity"

    def test_me_endpoint_exposes_resolved_ui_config_and_sources(self, bootstrap_tenant):
        tenant = bootstrap_tenant("theme-case-me")
        entity = tenant["entity"]

        theme_b = _make_theme("B")
        entity.theme = theme_b
        entity.save()

        response = tenant["client"].get("/api/me/")

        assert response.status_code == 200, response.data
        assert response.data["ui_sources"]["theme"] == "entity"
        assert response.data["ui_config"]["theme"]["name"] == "B"

    def test_user_theme_override_updates_through_the_users_endpoint(self, bootstrap_tenant):
        """O Theme Studio (scope="user") grava directamente via PATCH
        neste endpoint - ver components/theme/useThemeStudio.js no
        quasar_resaas."""
        tenant = bootstrap_tenant("theme-case-patch")
        user = tenant["user"]

        theme_c = _make_theme("C")

        response = tenant["client"].patch(
            f"/api/django_resaas/users/{user.id}/",
            {"theme": str(theme_c.id)},
            content_type="application/json",
        )

        assert response.status_code == 200, response.data

        user.refresh_from_db()
        assert user.theme_id == theme_c.id

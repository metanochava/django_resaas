"""Default language per EntityType, Entity and User.

User.get_effective_language(entity) resolves User > Entity > EntityType >
platform default (LanguageService.PLATFORM_DEFAULT_CODE). /api/me/ returns the
effective language of the signed context's Entity, and the account saves its
own choice (or clears it, null = inherit) through PATCH users/{id}/, the same
self-service path as the personal theme.
"""
import pytest

from django_resaas.saas.models.language import Language
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def languages():
    pt, _ = Language.objects.get_or_create(code="pt-pt", defaults={"name": "Português"})
    en, _ = Language.objects.get_or_create(code="en-us", defaults={"name": "English"})
    return pt, en


class TestEffectiveLanguage:

    def test_platform_default_when_no_level_chose_one(self, bootstrap_tenant, languages):
        pt, _en = languages
        tenant = bootstrap_tenant("lang-platform")

        assert tenant["user"].get_effective_language(tenant["entity"]) == pt
        assert tenant["user"].get_ui_sources(tenant["entity"])["language"] is None

    def test_entity_type_default(self, bootstrap_tenant, languages):
        _pt, en = languages
        tenant = bootstrap_tenant("lang-type")
        entity = tenant["entity"]
        entity.entity_type.language = en
        entity.entity_type.save()

        assert tenant["user"].get_effective_language(entity) == en
        assert tenant["user"].get_ui_sources(entity)["language"] == "entity_type"

    def test_entity_overrides_entity_type(self, bootstrap_tenant, languages):
        pt, en = languages
        tenant = bootstrap_tenant("lang-entity")
        entity = tenant["entity"]
        entity.entity_type.language = en
        entity.entity_type.save()
        entity.language = pt
        entity.save()

        assert tenant["user"].get_effective_language(entity) == pt
        assert tenant["user"].get_ui_sources(entity)["language"] == "entity"

    def test_user_overrides_entity(self, bootstrap_tenant, languages):
        pt, en = languages
        tenant = bootstrap_tenant("lang-user")
        entity = tenant["entity"]
        entity.language = pt
        entity.save()
        user = tenant["user"]
        user.language = en
        user.save()

        assert user.get_effective_language(entity) == en
        assert user.get_ui_sources(entity)["language"] == "user"


class TestMeLanguage:

    def test_me_returns_the_effective_language_of_the_context_entity(self, bootstrap_tenant, languages):
        _pt, en = languages
        tenant = bootstrap_tenant("lang-me")
        tenant["entity"].language = en
        tenant["entity"].save()

        response = tenant["client"].get("/api/me/")

        assert response.status_code == 200, response.data
        assert response.data["language"]["code"] == "en-us"
        assert response.data["own_language"] is None
        assert response.data["ui_sources"]["language"] == "entity"

    def test_the_user_saves_and_clears_their_own_language(self, bootstrap_tenant, languages):
        _pt, en = languages
        tenant = bootstrap_tenant("lang-save")
        user = tenant["user"]

        response = tenant["client"].patch(
            f"/api/django_resaas/users/{user.id}/", {"language": en.id}, content_type="application/json",
        )
        assert response.status_code == 200, response.data
        assert User.objects.get(pk=user.pk).language_id == en.id
        # the test client is force-authenticated with this instance
        user.refresh_from_db()
        me = tenant["client"].get("/api/me/").data
        assert me["own_language"] == en.id
        assert me["language"]["code"] == "en-us"

        response = tenant["client"].patch(
            f"/api/django_resaas/users/{user.id}/", {"language": None}, content_type="application/json",
        )
        assert response.status_code == 200, response.data
        assert User.objects.get(pk=user.pk).language_id is None


class TestLoginScreenLanguage:

    def test_the_public_entity_type_list_carries_its_default_language(self, bootstrap_tenant, languages):
        from rest_framework.test import APIClient

        _pt, en = languages
        tenant = bootstrap_tenant("lang-public")
        entity_type = tenant["entity"].entity_type
        entity_type.language = en
        entity_type.save()

        response = APIClient().get("/api/django_resaas/entitytypes/")

        assert response.status_code == 200, response.data
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        row = next(r for r in rows if str(r["id"]) == str(entity_type.id))
        assert row["language"] == {"id": en.id, "name": en.name, "code": "en-us"}

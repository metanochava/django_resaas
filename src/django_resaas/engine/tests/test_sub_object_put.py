"""Regressão: themePut/layoutSettingsPut/typographyPut/
animationSettingsPut em EntityAPIView e EntityTypeAPIView.

RepresentationMixin.to_representation() (engine/core/base/mixins/
serializer/representation.py) representa qualquer campo com
`choices=` como {"id","value","label"} - `Theme.state` é exactamente
esse caso (varchar(8), choices=Active/Inactive). O fluxo real do
Theme Studio é: themeGet -> editar cores -> themePut com o objecto
INTEIRO de volta (incluindo campos nunca tocados, como `state`) - sem
desembrulhar esse dict antes de `setattr`, isto rebentava com
`DataError: value too long for type character varying(8)` mesmo sem o
utilizador tocar em `state`.
"""
import pytest

pytestmark = pytest.mark.django_db


class TestEntityThemePut:

    def test_theme_get_represents_state_as_choice_dict(self, bootstrap_tenant):
        """Confirma a pré-condição do bug: themeGet devolve 'state'
        como {"id","value","label"}, não uma string simples."""
        tenant = bootstrap_tenant("theme-get")

        response = tenant["client"].get(
            f"/api/django_resaas/entitys/{tenant['entity'].id}/themeGet/"
        )

        assert response.status_code == 200, response.data
        assert isinstance(response.data["state"], dict)
        assert response.data["state"]["value"] == "Active"

    def test_theme_put_with_untouched_roundtrip_does_not_crash(self, bootstrap_tenant):
        """O cenário real do Theme Studio: carrega o tema (Get),
        edita só uma cor, e envia o objecto INTEIRO de volta (Put) -
        'state' nunca foi tocado pelo utilizador mas viaja no payload
        na forma de dict.

        Nota: quando a Entity ainda não tem o seu próprio Theme,
        themeGet devolve o da EntityType (partilhado), mas themePut
        cria um Theme NOVO (dedicado a esta Entity) na primeira
        gravação - por isso vamos buscar o theme pela Entity
        reconsultada, não pelo id devolvido por themeGet."""
        tenant = bootstrap_tenant("theme-put")

        get_response = tenant["client"].get(
            f"/api/django_resaas/entitys/{tenant['entity'].id}/themeGet/"
        )
        theme_payload = dict(get_response.data)
        theme_payload["primary"] = "#123456"  # única alteração real do utilizador

        put_response = tenant["client"].put(
            f"/api/django_resaas/entitys/{tenant['entity'].id}/themePut/",
            theme_payload,
            content_type="application/json",
        )

        assert put_response.status_code == 200, put_response.data

        from django_resaas.engine.models.entity import Entity

        entity = Entity.objects.get(id=tenant["entity"].id)
        assert entity.theme is not None
        assert entity.theme.state == "Active"
        assert entity.theme.primary == "#123456"

    def test_theme_put_ignores_id_and_timestamps_from_payload(self, bootstrap_tenant):
        tenant = bootstrap_tenant("theme-put-idfields")

        get_response = tenant["client"].get(
            f"/api/django_resaas/entitys/{tenant['entity'].id}/themeGet/"
        )

        theme_payload = dict(get_response.data)
        theme_payload["id"] = "11111111-1111-1111-1111-111111111111"
        theme_payload["created_at"] = "2000-01-01T00:00:00Z"

        put_response = tenant["client"].put(
            f"/api/django_resaas/entitys/{tenant['entity'].id}/themePut/",
            theme_payload,
            content_type="application/json",
        )

        assert put_response.status_code == 200, put_response.data

        from django_resaas.engine.models.entity import Entity

        entity = Entity.objects.get(id=tenant["entity"].id)
        assert str(entity.theme.id) != "11111111-1111-1111-1111-111111111111"


class TestEntityTypeThemePut:

    def test_theme_put_on_entity_type_does_not_crash(self, bootstrap_tenant):
        tenant = bootstrap_tenant("type-theme-put")
        entity_type = tenant["entity"].entity_type

        get_response = tenant["client"].get(
            f"/api/django_resaas/entitytypes/{entity_type.id}/themeGet/"
        )
        assert get_response.status_code == 200, get_response.data

        theme_payload = dict(get_response.data)
        theme_payload["secondary"] = "#abcdef"

        put_response = tenant["client"].put(
            f"/api/django_resaas/entitytypes/{entity_type.id}/themePut/",
            theme_payload,
            content_type="application/json",
        )

        assert put_response.status_code == 200, put_response.data

        from django_resaas.engine.models.theme import Theme

        theme = Theme.objects.get(id=get_response.data["id"])
        assert theme.state == "Active"
        assert theme.secondary == "#abcdef"

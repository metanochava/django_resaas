from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.core.services.interface_config_service import (
    InterfaceConfigService,
)
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.user import User
from django_resaas.saas.models.language import Language

from rest_framework import serializers


class MeSerializer(BaseSerializer):

    language = serializers.SerializerMethodField()
    interface_config = serializers.SerializerMethodField()
    ui_config = serializers.SerializerMethodField()
    ui_sources = serializers.SerializerMethodField()

    def _tenant_objects(self):
        request = self.context.get("request")

        entity = Entity.objects.filter(
            id=getattr(request, "entity_id", None)
        ).first() if request else None

        entity_type = EntityType.objects.filter(
            id=getattr(request, "entity_type_id", None)
        ).first() if request else None

        return entity, entity_type

    def get_interface_config(self, obj):
        """Header/footer já resolvidos (Entity > EntityType > default)
        - prontos para o frontend aplicar directamente, ver
        InterfaceConfigService.

        Não há aqui um nível de personalização por-utilizador (ver
        InterfaceConfigService) - essa personalização pessoal vive em
        obj.theme (+ ThemeSurface), já exposto via a resolução
        User > Entity > EntityType de get_ui_config/get_ui_sources em
        django_resaas.saas.models.user.User."""

        entity, entity_type = self._tenant_objects()

        return InterfaceConfigService.resolve(
            entity=entity, entity_type=entity_type
        )

    def get_ui_config(self, obj):
        """theme/layout/typography/animation já resolvidos
        (User > Entity > EntityType), ver User.get_ui_config()."""

        entity, _entity_type = self._tenant_objects()

        return obj.get_ui_config(entity)

    def get_ui_sources(self, obj):
        """De onde veio cada valor de get_ui_config - 'user' | 'entity'
        | 'entity_type' | None, ver User.get_ui_sources()."""

        entity, _entity_type = self._tenant_objects()

        return obj.get_ui_sources(entity)

    def get_language(self, obj):

        language = getattr(
            obj,
            "language",
            None
        )

        if not language:

            language = Language.objects.filter(
                code="pt-pt"
            ).first()

        if not language:
            return None

        return {
            "id": language.id,
            "name": language.name,
            "code": language.code,
        }

    class Meta:

        model = User

        fields = [
            "id",
            "email",
            "username",
            "profile",
            "mobile",
            "language",
            "last_login",
            "interface_config",

            # Overrides pessoais em bruto (FK own-level, null = herdar
            # de Entity/EntityType) - usados pelo Theme Studio para
            # saber se o User tem override próprio, distinto do valor
            # já resolvido em ui_config/ui_sources.
            "theme",
            "layout_settings",
            "typography",
            "animation_settings",

            "ui_config",
            "ui_sources",
        ]
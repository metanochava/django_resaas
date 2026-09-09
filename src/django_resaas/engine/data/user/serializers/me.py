from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.core.services.interface_config_service import (
    InterfaceConfigService,
)
from django_resaas.engine.models.entity import Entity
from django_resaas.engine.models.entity_type import EntityType
from django_resaas.engine.models.user import User
from django_resaas.engine.models.language import Language

from rest_framework import serializers


class MeSerializer(BaseSerializer):

    language = serializers.SerializerMethodField()
    interface_config = serializers.SerializerMethodField()
    interface_override = serializers.SerializerMethodField()

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
        """Header/footer já resolvidos (User > Entity > EntityType >
        default) - prontos para o frontend aplicar directamente, ver
        InterfaceConfigService."""

        entity, entity_type = self._tenant_objects()

        return InterfaceConfigService.resolve(
            user=obj, entity=entity, entity_type=entity_type
        )

    def get_interface_override(self, obj):
        """Só o que o PRÓPRIO utilizador personalizou (None = a
        herdar) - para um formulário de edição saber o estado actual
        sem confundir com o valor herdado."""

        return InterfaceConfigService.resolve_override_only(user=obj)

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
            "interface_override",
        ]
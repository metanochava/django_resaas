from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.user import User

from rest_framework import serializers


class MeSerializer(BaseSerializer):

    language = serializers.SerializerMethodField()
    # the user's own choice (id), null = inherits from the Entity/EntityType;
    # `language` above is the effective one
    own_language = serializers.SerializerMethodField()
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
        """The effective language: User > Entity > EntityType > platform
        default (User.get_effective_language)."""

        entity, _entity_type = self._tenant_objects()

        language = obj.get_effective_language(entity)

        if not language:
            return None

        return {
            "id": language.id,
            "name": language.name,
            "code": language.code,
        }

    def get_own_language(self, obj):
        return obj.language_id

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # RepresentationMixin rewrites every model FK by name, which would put
        # the user's OWN language (often null) back in "language": keep the
        # effective one there (own_language holds the user's choice)
        data["language"] = self.get_language(instance)
        return data

    class Meta:

        model = User

        fields = [
            "id",
            "email",
            "username",
            "profile",
            "mobile",
            # the account's own verification state (read-only): the Account
            # Center shows "verified" only from these, never guesses it
            "is_verified_email",
            "is_verified_mobile",
            "password_changed_at",
            "language",
            "own_language",
            "last_login",

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
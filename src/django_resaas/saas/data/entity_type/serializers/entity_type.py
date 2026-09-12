from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_group import EntityTypeGroup


class EntityTypeSerializer(BaseSerializer):
    permanent_fields_files = ["icon"]

    login_background = serializers.SerializerMethodField()
    login_config = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    state_display = serializers.CharField(
        source="get_state_display",
        read_only=True,
    )

    def _login_surface(self, obj):
        # Ver EntitySerializer._login_surface (mesmo motivo: os campos
        # login_background_* deixaram de existir no modelo - a origem
        # actual é ThemeSurface, area='login', do Theme efectivo).
        theme = obj.theme

        if not theme:
            return None

        return theme.surfaces.filter(area="login").first()

    def get_login_background(self, obj):
        surface = self._login_surface(obj)

        if not surface or surface.background_type in (None, "transparent"):
            return {
                "type": "color",
                "value": "#ffffff",
            }

        if surface.background_type == "image":
            if not surface.background_image:
                return None

            file_data = self._file_representation(
                self.context.get("request"),
                surface.background_image,
                "background_image",
            )

            return {
                "type": "image",
                "value": file_data["url"],
                "file": file_data,
            } if file_data else None

        if surface.background_type == "gradient":
            return {
                "type": "gradient",
                "value": surface.background_gradient,
            } if surface.background_gradient else None

        return {
            "type": "color",
            "value": surface.background_color or "#ffffff",
        }

    def get_login_config(self, obj):
        layout = obj.layout_settings
        surface = self._login_surface(obj)

        return {
            "position": (layout.login_position if layout else None) or "center",
            "background": self.get_login_background(obj),
            "overlay": surface.background_overlay if surface else None,
        }

    def get_groups(self, obj):
        return [
            {
                "id": item.group.id,
                "name": item.group.name,
            }
            for item in EntityTypeGroup.objects.filter(
                entity_type_id=obj.id
            ).select_related("group")
        ]

    class Meta:
        model = EntityType
        fields = "__all__"
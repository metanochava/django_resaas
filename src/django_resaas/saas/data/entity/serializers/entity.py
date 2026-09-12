from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.entity import Entity


class EntitySerializer(BaseSerializer):
    permanent_fields_files = ["logo"]

    login_background = serializers.SerializerMethodField()
    login_config = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = "__all__"

    def _login_surface(self, obj):
        # Fundo do login já não vive em campos soltos no próprio
        # Entity (login_background_type/color/gradient/image) - esses
        # campos deixaram de existir no modelo. A origem actual é
        # ThemeSurface (area='login') do Theme efectivo desta Entity -
        # ver django_resaas.saas.models.theme_surface.ThemeSurface e
        # CLAUDE.md (quasar_resaas) secção 21: "aparência = ThemeSurface".
        theme = obj.theme

        if not theme:
            return None

        return theme.surfaces.filter(area="login").first()

    def get_login_background(self, obj):
        surface = self._login_surface(obj)

        if not surface or surface.background_type in (None, "transparent"):
            return None

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

        values = {
            "gradient": surface.background_gradient,
            "color": surface.background_color,
        }

        value = values.get(surface.background_type)

        return {
            "type": surface.background_type,
            "value": value,
        } if value else None

    def get_login_config(self, obj):
        # A posição continua a pertencer ao LayoutSetting efectivo
        # (não a ThemeSurface) - CLAUDE.md (quasar_resaas) secção 21:
        # "posição = LayoutSetting".
        layout = obj.layout_settings
        surface = self._login_surface(obj)

        return {
            "position": layout.login_position if layout else None,
            "background": self.get_login_background(obj),
            "overlay": surface.background_overlay if surface else None,
        }
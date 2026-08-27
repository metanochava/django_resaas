from rest_framework import serializers

from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entity import Entity


class EntitySerializer(BaseSerializer):
    permanent_fields_files = ["logo"]

    login_background = serializers.SerializerMethodField()
    login_config = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = "__all__"

    def get_login_background(self, obj):
        if obj.login_background_type == "image":
            if not obj.login_background_image:
                return None

            file_data = self._file_representation(
                self.context.get("request"),
                obj.login_background_image,
                "login_background_image",
            )

            return {
                "type": "image",
                "value": file_data["url"],
                "file": file_data,
            } if file_data else None

        values = {
            "gradient": obj.login_background_gradient,
            "color": obj.login_background_color,
        }

        value = values.get(obj.login_background_type)

        return {
            "type": obj.login_background_type,
            "value": value,
        } if value else None

    def get_login_config(self, obj):
        return {
            "position": obj.login_position,
            "background": self.get_login_background(obj),
            "overlay": obj.login_background_overlay,
        }
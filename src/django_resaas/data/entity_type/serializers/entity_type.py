from rest_framework import serializers

from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity_type_group import EntityTypeGroup


class EntityTypeSerializer(BaseSerializer):
    permanent_fields_files = ["icon"]

    login_background = serializers.SerializerMethodField()
    login_config = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    state_display = serializers.CharField(
        source="get_state_display",
        read_only=True,
    )

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

        if obj.login_background_type == "gradient":
            return {
                "type": "gradient",
                "value": obj.login_background_gradient,
            } if obj.login_background_gradient else None

        return {
            "type": "color",
            "value": obj.login_background_color or "#ffffff",
        }

    def get_login_config(self, obj):
        return {
            "position": obj.login_position or "center",
            "background": self.get_login_background(obj),
            "overlay": obj.login_background_overlay,
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
from rest_framework import serializers

from django.contrib.contenttypes.models import ContentType


class ModeloSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = [
            "id",
            "app_label",
            "model",
        ]

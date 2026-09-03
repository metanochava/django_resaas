from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.file import File


class FileGravarSerializer(BaseSerializer):
    class Meta:
        model = File
        fields = "__all__"

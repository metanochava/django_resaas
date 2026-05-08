from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.file import File


class FileGravarSerializer(BaseSerializer):
    class Meta:
        model = File
        fields = "__all__"

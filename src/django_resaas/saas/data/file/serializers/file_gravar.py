from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.file import File


class FileGravarSerializer(BaseSerializer):
    class Meta:
        model = File
        fields = "__all__"

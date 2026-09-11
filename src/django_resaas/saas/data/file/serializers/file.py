from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.file import File


class FileSerializer(BaseSerializer):
    class Meta:
        model = File
        fields = [
            'id',
            'file',
            'size',
            'model',
            'state',
            'chamador',
            'funcionalidade',

        ]

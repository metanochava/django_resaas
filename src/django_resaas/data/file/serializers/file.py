from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.file import File


class FileSerializer(BaseSerializer):
    class Meta:
        model = File
        fields = [
            'id',
            'file',
            'size',
            'model',
            'estado',
            'chamador',
            'funcionalidade',

        ]

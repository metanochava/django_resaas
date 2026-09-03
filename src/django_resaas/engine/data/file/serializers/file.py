from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.file import File


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

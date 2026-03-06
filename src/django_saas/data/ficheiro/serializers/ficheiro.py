from django_saas.core.base.serializers import BaseSerializer
from django_saas.models.ficheiro import Ficheiro


class FicheiroSerializer(BaseSerializer):
    class Meta:
        model = Ficheiro
        fields = [
            'id',
            'ficheiro',
            'size',
            'modelo',
            'estado',
            'chamador',
            'funcionalidade',

        ]

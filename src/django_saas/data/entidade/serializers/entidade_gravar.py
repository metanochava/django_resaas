from django_saas.core.base.serializers import BaseSerializer
from django_saas.models.entidade import Entidade


class EntidadeGravarSerializer(BaseSerializer):
    permanent_fields_files = ['logo']

    class Meta:
        model = Entidade
        fields = [
            'id',
            'nome',
            'logo',
            'groups',
            'admins',
            'modelos',
            'display_logo',
            'display_qr',
            'display_bar',
            'tipo_entidade',
            'disc_space',
            'disc_used_space',
            'disc_free_space',
            'rodape',
            'estado',
        ]
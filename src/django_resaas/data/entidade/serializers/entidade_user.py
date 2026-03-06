from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entidade import Entidade


class EntidadeUserSerializer(BaseSerializer):
    permanent_fields_files = ['logo']

    class Meta:
        model = Entidade
        fields = "__all__"
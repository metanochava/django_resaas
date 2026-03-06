from django_saas.core.base.serializers import BaseSerializer
from django_saas.models.entidade import Entidade


class EntidadeUserSerializer(BaseSerializer):
    permanent_fields_files = ['logo']

    class Meta:
        model = Entidade
        fields = "__all__"
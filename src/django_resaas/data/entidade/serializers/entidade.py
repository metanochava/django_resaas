from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entidade import Entidade


class EntidadeSerializer(BaseSerializer):
    tipo_entidade = serializers.PrimaryKeyRelatedField(
        queryset=TipoEntidade.objects.all(),
        required=False
    )

    admins = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False
    )
    permanent_fields_files = ['logo']
    class Meta:
        model = Entidade
        fields = "__all__"

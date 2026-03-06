from rest_framework import serializers

from django_saas.core.base.serializers import BaseSerializer
from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.data.group.serializers.grupo import GrupoSerializer

from django_saas.models.tipo_entidade_group import TipoEntidadeGroup



class TipoEntidadeSerializer(BaseSerializer):
    permanent_fields_files = ['icon']
    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True
    )


    groups = serializers.SerializerMethodField()

    def get_groups(self, obj):
        tietgr = []
        for teg in TipoEntidadeGroup.objects.filter(tipo_entidade__id=obj.id):
            tietgr.append({'id':teg.group.id, 'name':teg.group.name})
        # print(tietgr)

        return tietgr

    class Meta:
        model = TipoEntidade
        fields = "__all__"

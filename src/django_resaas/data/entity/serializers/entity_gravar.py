from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entity import Entity


class EntityGravarSerializer(BaseSerializer):
    permanent_fields_files = ['logo']

    class Meta:
        model = Entity
        fields =  "__all__"
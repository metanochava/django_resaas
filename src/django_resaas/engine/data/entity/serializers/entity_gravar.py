from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.entity import Entity


class EntityGravarSerializer(BaseSerializer):
    permanent_fields_files = ['logo']

    class Meta:
        model = Entity
        fields =  "__all__"
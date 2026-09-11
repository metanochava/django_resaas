from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.entity import Entity


class EntityGravarSerializer(BaseSerializer):
    permanent_fields_files = ['logo']

    class Meta:
        model = Entity
        fields =  "__all__"
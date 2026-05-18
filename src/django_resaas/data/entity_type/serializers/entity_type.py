from rest_framework import serializers

from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entity_type import EntityType
from django_resaas.data.group.serializers.group import GroupSerializer

from django_resaas.models.entity_type_group import EntityTypeGroup



class EntityTypeSerializer(BaseSerializer):
    permanent_fields_files = ['icon']
    state_display = serializers.CharField(
        source="get_state_display",
        read_only=True
    )


    groups = serializers.SerializerMethodField()

    def get_groups(self, obj):
        tietgr = []
        for teg in EntityTypeGroup.objects.filter(entity_type__id=obj.id):
            tietgr.append({'id':teg.group.id, 'name':teg.group.name})


        return tietgr

    class Meta:
        model = EntityType
        fields = "__all__"

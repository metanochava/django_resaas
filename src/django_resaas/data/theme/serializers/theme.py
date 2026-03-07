from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.theme import Theme


class ThemeSerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = Theme
        fields = "__all__"

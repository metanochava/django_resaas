from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.theme import Theme, Typography


class ThemeSerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = Theme
        fields = "__all__"

class TypographySerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = Typography
        fields = "__all__"

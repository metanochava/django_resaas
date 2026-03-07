from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.layout_setting import LayoutSetting


class LayoutSettingSerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = LayoutSetting
        fields = "__all__"

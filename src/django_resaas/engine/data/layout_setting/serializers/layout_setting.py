from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.layout_setting import LayoutSetting, AnimationSetting


class LayoutSettingSerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = LayoutSetting
        fields = "__all__"


class AnimationSettingSerializer(BaseSerializer):
    permanent_fields_files = []
    class Meta:
        model = AnimationSetting
        fields = "__all__"

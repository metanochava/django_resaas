
from django_resaas.saas.core.base.access import ExplicitAccessMixin
from rest_framework import filters
from rest_framework import viewsets


from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer


class LayoutSettingAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)

    filter_backends = (filters.SearchFilter,)
    serializer_class = LayoutSettingSerializer
    queryset = LayoutSetting.objects.all()

    def get_queryset(self):
        return self.queryset.filter()
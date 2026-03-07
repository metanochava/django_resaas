
from rest_framework import filters
from rest_framework import viewsets


from django_resaas.models.layout_setting import LayoutSetting
from django_resaas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer


class LayoutSettingAPIView(viewsets.ModelViewSet):
    filter_backends = (filters.SearchFilter,)
    serializer_class = LayoutSettingSerializer
    queryset = LayoutSetting.objects.all()

    def get_queryset(self):
        return self.queryset.filter()
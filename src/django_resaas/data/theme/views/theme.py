
from rest_framework import filters
from rest_framework import viewsets


from django_resaas.models.theme import Theme
from django_resaas.data.theme.serializers.theme import ThemeSerializer


class ThemeAPIView(viewsets.ModelViewSet):
    filter_backends = (filters.SearchFilter,)
    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    def get_queryset(self):
        return self.queryset.filter()
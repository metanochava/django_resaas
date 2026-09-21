
from django_resaas.saas.core.base.access import ExplicitAccessMixin
from rest_framework import filters
from rest_framework import viewsets


from django_resaas.saas.models.theme import Theme
from django_resaas.saas.data.theme.serializers.theme import ThemeSerializer


class ThemeAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)

    filter_backends = (filters.SearchFilter,)
    serializer_class = ThemeSerializer
    queryset = Theme.objects.all()

    def get_queryset(self):
        return self.queryset.filter()
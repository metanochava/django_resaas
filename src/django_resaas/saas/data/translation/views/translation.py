
from rest_framework import filters
from rest_framework import viewsets

from django_resaas.saas.core.utils.pagination import ResaasPagination
from django_resaas.saas.models.translation import Translation
from django_resaas.saas.data.translation.serializers.translation import TranslationSerializer


class TranslationAPIView(viewsets.ModelViewSet):
    # Was querying Language/LanguageSerializer - a copy-paste bug that
    # meant GET django_resaas/translations/ actually served Language
    # rows, never a single real Translation (chave/translation) row.
    search_fields = ["chave", "translation"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = TranslationSerializer
    queryset = Translation.objects.all()
    lookup_field = "id"
    pagination_class = ResaasPagination

    def get_queryset(self):
        return self.queryset.select_related("language").order_by(
            "language__name", "chave"
        )
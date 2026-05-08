
from rest_framework import filters
from rest_framework import viewsets


from django_resaas.models.language import Language
from django_resaas.data.language.serializers.language import LanguageSerializer


class TranslationAPIView(viewsets.ModelViewSet):
    filter_backends = (filters.SearchFilter,)
    serializer_class = LanguageSerializer
    queryset = Language.objects.all()

    def get_queryset(self):
        return self.queryset.filter()
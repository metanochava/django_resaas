
from rest_framework import filters
from rest_framework import viewsets


from django_saas.models.idioma import Idioma
from django_saas.data.idioma.serializers.idioma import IdiomaSerializer


class TraducaoAPIView(viewsets.ModelViewSet):
    filter_backends = (filters.SearchFilter,)
    serializer_class = IdiomaSerializer
    queryset = Idioma.objects.all()

    def get_queryset(self):
        return self.queryset.filter()
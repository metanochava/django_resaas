
# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from django_resaas.models.person import Person
from django_resaas.core.base.views import BaseAPIView

from django_resaas.data.person.serializers.person import PersonSerializer

class  PersonAPIView(BaseAPIView):

    filter_backends = (filters.SearchFilter,)
    
    serializer_class = PersonSerializer
    queryset = Person.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter().order_by('-id')
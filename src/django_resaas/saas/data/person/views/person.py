
# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from django_resaas.saas.models.person import Person
from django_resaas.saas.core.base.views import BaseAPIView, registerView

from django_resaas.saas.data.person.serializers.person import PersonSerializer

@registerView('persons')
class  PersonAPIView(BaseAPIView):
    serializer_class = PersonSerializer
    queryset = Person.objects.all()
    lookup_field = "id"


# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from django_resaas.engine.models.person import Person
from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.engine.data.person.serializers.person import PersonSerializer

@registerView('persons')
class  PersonAPIView(BaseAPIView):
    serializer_class = PersonSerializer
    queryset = Person.objects.all()
    lookup_field = "id"

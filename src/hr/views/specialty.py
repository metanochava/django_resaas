# hr/views/specialty.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.specialty import Specialty
from hr.serializers.specialty import SpecialtySerializer


@registerView('specialties')
class SpecialtyAPIView(BaseAPIView):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
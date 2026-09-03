# hr/views/specialty.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.specialty import Specialty
from django_resaas.hr.serializers.specialty import SpecialtySerializer


@registerView('specialtys', module='hr')
class SpecialtyAPIView(BaseAPIView):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
# hr/views/competency.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.competency import Competency
from django_resaas.hr.serializers.competency import CompetencySerializer


@registerView('competencies', module='hr')
class CompetencyAPIView(BaseAPIView):
    queryset = Competency.objects.all()
    serializer_class = CompetencySerializer

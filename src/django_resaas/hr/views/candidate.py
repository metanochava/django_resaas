# hr/views/candidate.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.candidate import Candidate
from django_resaas.hr.serializers.candidate import CandidateSerializer


@registerView('candidates', module='hr')
class CandidateAPIView(BaseAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

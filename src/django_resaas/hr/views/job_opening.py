# hr/views/job_opening.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.job_opening import JobOpening
from django_resaas.hr.serializers.job_opening import JobOpeningSerializer


@registerView('jobopenings', module='hr')
class JobOpeningAPIView(BaseAPIView):
    queryset = JobOpening.objects.all()
    serializer_class = JobOpeningSerializer

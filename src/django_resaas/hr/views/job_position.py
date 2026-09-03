# hr/views/job_position.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.job_position import JobPosition
from django_resaas.hr.serializers.job_position import JobPositionSerializer


@registerView('jobpositions', module='hr')
class JobPositionAPIView(BaseAPIView):
    queryset = JobPosition.objects.all()
    serializer_class = JobPositionSerializer
# hr/views/job_position.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.job_position import JobPosition
from hr.serializers.job_position import JobPositionSerializer


@registerView('jobpositions')
class JobPositionAPIView(BaseAPIView):
    queryset = JobPosition.objects.all()
    serializer_class = JobPositionSerializer
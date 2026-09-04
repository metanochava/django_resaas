# hr/views/job_grade.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.job_grade import JobGrade
from django_resaas.hr.serializers.job_grade import JobGradeSerializer


@registerView('jobgrades', module='hr')
class JobGradeAPIView(BaseAPIView):
    queryset = JobGrade.objects.all()
    serializer_class = JobGradeSerializer

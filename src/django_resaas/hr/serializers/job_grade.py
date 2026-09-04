# hr/serializers/job_grade.py

from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.job_grade import JobGrade


class JobGradeSerializer(BaseSerializer):

    class Meta:
        model = JobGrade
        fields = "__all__"

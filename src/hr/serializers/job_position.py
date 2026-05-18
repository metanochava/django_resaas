# hr/serializers/job_position.py

from rest_framework import serializers
from django_resaas.core.base.serializers import BaseSerializer

from hr.models.job_position import JobPosition
from hr.models.department import Department

from hr.serializers.department import DepartmentSerializer


class JobPositionSerializer(BaseSerializer):

    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    department_data = DepartmentSerializer(
        source='department',
        read_only=True
    )

    class Meta:
        model = JobPosition
        fields = "__all__"
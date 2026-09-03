
# hr/serializers/employee.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.employee import Employee
from django_resaas.hr.models.job_position import JobPosition

from django_resaas.engine.models.person import Person

from django_resaas.engine.data.person.serializers.person import PersonSerializer
from django_resaas.hr.serializers.job_position import JobPositionSerializer


class EmployeeSerializer(BaseSerializer):

    person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        write_only=True
    )

    person_data = PersonSerializer(
        source='person',
        read_only=True
    )

    position = serializers.PrimaryKeyRelatedField(
        queryset=JobPosition.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    position_data = JobPositionSerializer(
        source='position',
        read_only=True
    )

    manager = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    manager_data = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = "__all__"

    def get_manager_data(self, obj):
        if not obj.manager:
            return None

        return {
            "id": obj.manager.id,
            "label": str(obj.manager)
        }
# hr/serializers/employee_specialty.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.employee_specialty import EmployeeSpecialty
from django_resaas.hr.models.employee import Employee
from django_resaas.hr.models.specialty import Specialty

from django_resaas.hr.serializers.employee import EmployeeSerializer
from django_resaas.hr.serializers.specialty import SpecialtySerializer


class EmployeeSpecialtySerializer(BaseSerializer):

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True
    )

    employee_data = EmployeeSerializer(
        source='employee',
        read_only=True
    )

    specialty = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.all(),
        write_only=True
    )

    specialty_data = SpecialtySerializer(
        source='specialty',
        read_only=True
    )

    class Meta:
        model = EmployeeSpecialty
        fields = "__all__"
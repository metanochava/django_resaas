# hr/serializers/shift_schedule.py

from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.shift_schedule import ShiftSchedule
from django_resaas.hr.models.employee import Employee
from django_resaas.hr.models.shift import Shift

from django_resaas.hr.serializers.employee import EmployeeSerializer
from django_resaas.hr.serializers.shift import ShiftSerializer


class ShiftScheduleSerializer(BaseSerializer):

    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True
    )

    employee_data = EmployeeSerializer(
        source='employee',
        read_only=True
    )

    shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects.all(),
        write_only=True
    )

    shift_data = ShiftSerializer(
        source='shift',
        read_only=True
    )

    class Meta:
        model = ShiftSchedule
        fields = "__all__"
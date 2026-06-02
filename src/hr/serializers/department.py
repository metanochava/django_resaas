# hr/serializers/department.py

from rest_framework import serializers
from django_resaas.core.base.serializers import BaseSerializer

from hr.models.department import Department
from hr.models.employee import Employee



class DepartmentSerializer(BaseSerializer):

    manager = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    manager_data = serializers.SerializerMethodField()

    def get_manager_data(self, obj):

        if not obj.manager:
            return None

        from hr.serializers.employee import EmployeeSerializer

        return EmployeeSerializer(
            obj.manager,
            context=self.context
        ).data

    class Meta:
        model = Department
        fields = "__all__"
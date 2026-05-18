# hr/serializers/salary_component.py

from django_resaas.core.base.serializers import BaseSerializer

from hr.models.salary_component import SalaryComponent


class SalaryComponentSerializer(BaseSerializer):

    class Meta:
        model = SalaryComponent
        fields = "__all__"
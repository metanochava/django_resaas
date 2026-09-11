# hr/serializers/salary_component.py

from django_resaas.saas.core.base.serializers import BaseSerializer

from django_resaas.hr.models.salary_component import SalaryComponent


class SalaryComponentSerializer(BaseSerializer):

    class Meta:
        model = SalaryComponent
        fields = "__all__"
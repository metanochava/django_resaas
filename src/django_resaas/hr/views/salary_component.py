# hr/views/salary_component.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.salary_component import SalaryComponent
from django_resaas.hr.serializers.salary_component import SalaryComponentSerializer


@registerView('salarycomponents', module='hr')
class SalaryComponentAPIView(BaseAPIView):
    queryset = SalaryComponent.objects.all()
    serializer_class = SalaryComponentSerializer
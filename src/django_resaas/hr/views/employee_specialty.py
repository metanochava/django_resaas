# hr/views/employee_specialty.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.employee_specialty import EmployeeSpecialty
from django_resaas.hr.serializers.employee_specialty import EmployeeSpecialtySerializer


@registerView('employeespecialtys', module='hr')
class EmployeeSpecialtyAPIView(BaseAPIView):
    queryset = EmployeeSpecialty.objects.all()
    serializer_class = EmployeeSpecialtySerializer
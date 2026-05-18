# hr/views/employee_specialty.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.employee_specialty import EmployeeSpecialty
from hr.serializers.employee_specialty import EmployeeSpecialtySerializer


@registerView('employeespecialties')
class EmployeeSpecialtyAPIView(BaseAPIView):
    queryset = EmployeeSpecialty.objects.all()
    serializer_class = EmployeeSpecialtySerializer
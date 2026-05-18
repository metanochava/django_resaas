# hr/views/department.py

from django_resaas.core.base.views import BaseAPIView, registerView

from hr.models.department import Department
from hr.serializers.department import DepartmentSerializer


@registerView('departments')
class DepartmentAPIView(BaseAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
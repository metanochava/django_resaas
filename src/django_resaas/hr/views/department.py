# hr/views/department.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.department import Department
from django_resaas.hr.serializers.department import DepartmentSerializer


@registerView('departments', module='hr')
class DepartmentAPIView(BaseAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
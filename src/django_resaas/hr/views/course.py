# hr/views/course.py

from django_resaas.engine.core.base.views import BaseAPIView, registerView

from django_resaas.hr.models.course import Course
from django_resaas.hr.serializers.course import CourseSerializer


@registerView('courses', module='hr')
class CourseAPIView(BaseAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

# hr/serializers/course.py

from django_resaas.engine.core.base.serializers import BaseSerializer

from django_resaas.hr.models.course import Course


class CourseSerializer(BaseSerializer):

    class Meta:
        model = Course
        fields = "__all__"

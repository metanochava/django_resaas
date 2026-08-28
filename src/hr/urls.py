
from django.urls import path, include
from rest_framework import routers
# from hr.views.employee import EmployeeAPIView


router = routers.DefaultRouter()
# router.register("employees", EmployeeAPIView, basename="employees")

urlpatterns = [
    path("hr", include(router.urls)),
]

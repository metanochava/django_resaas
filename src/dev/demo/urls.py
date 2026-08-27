from django.urls import path, include
from rest_framework import routers

from dev.demo.views import ProductAPIView

router = routers.DefaultRouter()
router.register("products", ProductAPIView, basename="products")

urlpatterns = [
    path("", include(router.urls)),
]

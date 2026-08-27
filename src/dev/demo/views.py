from django_resaas.core.base.views import BaseAPIView, registerView

from dev.demo.models import Product
from dev.demo.serializers import ProductSerializer


@registerView(module="demo")
class ProductAPIView(BaseAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

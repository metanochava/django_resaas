from django_resaas.saas.core.base.serializers import BaseSerializer

from dev.demo.models import Product


class ProductSerializer(BaseSerializer):
    class Meta:
        model = Product
        fields = "__all__"

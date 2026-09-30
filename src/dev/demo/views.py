from django_resaas.saas.core.base.views import BaseAPIView, registerView

from dev.demo.models import Agreement, Category, Member, Product, Rate, Visit
from dev.demo.serializers import (
    AgreementSerializer,
    CategorySerializer,
    MemberSerializer,
    ProductSerializer,
    RateSerializer,
    VisitSerializer,
)


@registerView(module="demo")
class ProductAPIView(BaseAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


@registerView("categories", module="demo")
class CategoryAPIView(BaseAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


@registerView("members", module="demo")
class MemberAPIView(BaseAPIView):
    queryset = Member.objects.select_related("person", "category", "manager")
    serializer_class = MemberSerializer


@registerView("rates", module="demo")
class RateAPIView(BaseAPIView):
    queryset = Rate.objects.all()
    serializer_class = RateSerializer


@registerView("visits", module="demo")
class VisitAPIView(BaseAPIView):
    queryset = Visit.objects.select_related("member")
    serializer_class = VisitSerializer


@registerView("agreements", module="demo")
class AgreementAPIView(BaseAPIView):
    queryset = Agreement.objects.select_related("member")
    serializer_class = AgreementSerializer

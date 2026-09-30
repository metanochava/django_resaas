from django_resaas.saas.core.base.serializers import BaseSerializer

from dev.demo.models import Agreement, Category, Member, Product, Rate, Visit


class ProductSerializer(BaseSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class CategorySerializer(BaseSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class MemberSerializer(BaseSerializer):
    class Meta:
        model = Member
        fields = "__all__"


class RateSerializer(BaseSerializer):
    class Meta:
        model = Rate
        fields = "__all__"


class VisitSerializer(BaseSerializer):
    class Meta:
        model = Visit
        fields = "__all__"


class AgreementSerializer(BaseSerializer):
    class Meta:
        model = Agreement
        fields = "__all__"

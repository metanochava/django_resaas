
from rest_framework import serializers


from django_resaas.saas.models.branch import Branch
from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.data.address.serializers.address import AddressSerializer


class BranchSerializer(BaseSerializer):
    """Branch inherits AddressMixin (core/base/mixins/address.py) -
    `address` here is that mixin's main Address row (geolocation +
    structured address, Google Maps-ready), nested read/write since it
    isn't a concrete field on Branch itself and `fields = "__all__"`
    would otherwise never surface it."""

    address = AddressSerializer(required=False, allow_null=True)

    class Meta:
        model = Branch
        fields = "__all__"

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)

        branch = super().create(validated_data)

        if address_data:
            branch.set_address(**address_data)

        return branch

    def update(self, instance, validated_data):
        address_data = validated_data.pop("address", None)

        branch = super().update(instance, validated_data)

        if address_data:
            branch.set_address(**address_data)

        return branch

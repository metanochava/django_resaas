
from rest_framework import serializers


from django_resaas.saas.models.person import Person
from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.data.address.serializers.address import AddressSerializer
from django_resaas.saas.data.user.serializers.user import UserSerializer

class PersonSerializer(BaseSerializer):
    # user_data = UserSerializer(source='user', read_only=True) # nao descomentar
    profile = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    # Person inherits AddressMixin (core/base/mixins/address.py) - see
    # BranchSerializer for the identical pattern/rationale.
    address = AddressSerializer(required=False, allow_null=True)

    class Meta:
        model = Person
        fields = "__all__"

    def get_profile(self, obj):
        if not obj.user:
            return None

        data = UserSerializer(obj.user,
            context={  **self.context, "include_fields": ["profile"], # 👈 escolhe aqui
        }).data
        return data['profile']

    def get_age(self, obj):
        # Person.age is a @property, not a method - obj.age() would try
        # to call its result (an int or None) as a function.
        return obj.age

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)

        person = super().create(validated_data)

        if address_data:
            person.set_address(**address_data)

        return person

    def update(self, instance, validated_data):
        address_data = validated_data.pop("address", None)

        # An empty photo on update means "no new photo", never "delete the
        # current one": every Person-based form (employee, patient, ...)
        # shows the existing photo in the same input, and an empty value
        # (null/"" from a cleared input or a client that resends the
        # whole record) must not wipe it. Only a real upload replaces it.
        if "photo" in validated_data and not validated_data["photo"]:
            validated_data.pop("photo")

        person = super().update(instance, validated_data)

        if address_data:
            person.set_address(**address_data)

        return person

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)

    #     valor = UserSerializer(instance.user, context={
    #             **self.context,
    #             "include_fields": ["profile"], # 👈 escolhe aqui
    #             "exclude_fields": ["user_permissions", "groups", "created_by", "updated_by", "created_by_id", "updated_by_id"]
    #         }).data if instance.user else None

    #     data["profile"] = valor['profile']
    #     return data



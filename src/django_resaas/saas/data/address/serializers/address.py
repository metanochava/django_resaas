from rest_framework import serializers

from django_resaas.saas.models.address import Address


class AddressSerializer(serializers.ModelSerializer):
    """Nested, reusable serializer for anything using AddressMixin
    (currently Branch - see BranchSerializer.address). Not registered
    as its own top-level CRUD resource: an address only ever makes
    sense attached to its owner, created/updated through
    AddressMixin.set_address() rather than directly.

    Excludes the generic-relation plumbing (content_type/object_id/
    content_object) and address_type - those are managed by the owning
    model's set_address()/get_address(), never set directly by a
    client."""

    coordinates = serializers.ReadOnlyField()
    full_address = serializers.ReadOnlyField()

    class Meta:
        model = Address
        fields = [
            "id",
            "place_id",
            "latitude",
            "longitude",
            "formatted_address",
            "street_number",
            "route",
            "premise",
            "subpremise",
            "neighborhood",
            "sublocality",
            "locality",
            "administrative_area_level_1",
            "administrative_area_level_2",
            "administrative_area_level_3",
            "postal_code",
            "country",
            "country_code",
            "complement",
            "full_address",
            "coordinates",
        ]
        read_only_fields = ["id"]

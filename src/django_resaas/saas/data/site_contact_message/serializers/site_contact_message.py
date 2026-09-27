from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.models.site_contact_message import SiteContactMessage


class SiteContactMessageInputSerializer(serializers.Serializer):
    """What a public visitor sends (POST site/contact/). The Entity and the
    site are not fields: they come from the request Origin."""

    name = serializers.CharField(max_length=150, trim_whitespace=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, trim_whitespace=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    # honeypot: hidden in the form, so only bots fill it in
    website = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # staff can only answer a visitor who left a way to be reached
        if not attrs.get("phone") and not attrs.get("email"):
            message = Translate.tdc(self.context.get("request"), "Enter a phone number or an email.")
            raise serializers.ValidationError({"phone": [message], "email": [message]})
        return attrs


class SiteContactMessageSerializer(BaseSerializer):
    """Staff view of a message (sitecontactmessages/): what the visitor wrote
    is read only; staff only change the status."""

    class Meta:
        model = SiteContactMessage
        fields = "__all__"
        read_only_fields = ["name", "phone", "email", "message"]

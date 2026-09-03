
from rest_framework import serializers

from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.user import User


class UserSerializer(BaseSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile', 'mobile']
        # email/mobile can NEVER change through a generic PATCH here -
        # ownership of the new value must be proven via OTP first (see
        # data/user/views/profile_contact_otp.py). Enforced server-side,
        # not just hidden in the frontend - see security-review discussion
        # in the session that added this.
        extra_kwargs = {
            'email': {'read_only': True},
            'mobile': {'read_only': True},
        }
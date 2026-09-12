
from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.user import User


class UserSerializer(BaseSerializer):

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'profile', 'mobile',
            # Overrides pessoais de aparência (null = herdar de
            # Entity/EntityType - ver User.get_effective_theme() /
            # get_ui_config()). Precisam de estar aqui para que o
            # Theme Studio (scope="user") consiga gravá-los via PATCH
            # neste endpoint (ver components/theme/useThemeStudio.js
            # no quasar_resaas).
            'theme', 'layout_settings', 'typography', 'animation_settings',
        ]
        # email/mobile can NEVER change through a generic PATCH here -
        # ownership of the new value must be proven via OTP first (see
        # data/user/views/profile_contact_otp.py). Enforced server-side,
        # not just hidden in the frontend - see security-review discussion
        # in the session that added this.
        extra_kwargs = {
            'email': {'read_only': True},
            'mobile': {'read_only': True},
        }
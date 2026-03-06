from rest_framework import serializers

from django_resaas.models.user import User
from django_resaas.core.utils.translate import Translate


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'mobile')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        request = self.context.get('request')
        username = attrs.get('username', '')

        if not username.isalnum():
            raise serializers.ValidationError(
                {
                    'username': Translate.tdc(
                        request,
                        'O nome de utilizador deve conter apenas caracteres alfanuméricos'
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

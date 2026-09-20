from django.db.models import Q

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from django_resaas.saas.models.user import User
from django_resaas.saas.core.utils.translate import Translate
from django.utils import timezone

from django_resaas.saas.core.services import session_service, temporary_password_service


def authenticate(value=None, password=None):
    try:
        user = User.objects.get(
            Q(email=value) |
            Q(username=value) |
            Q(mobile=value)
        )
    except User.DoesNotExist:
        return None

    if user.check_password(password):
        # a temporary password is not a login yet (no session until it is
        # replaced), so it must not look like the account was ever used
        if not user.must_change_password:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

        return user

    return None

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    username = serializers.CharField(read_only=True)
    mobile = serializers.CharField(read_only=True, allow_null=True)
    tokens = serializers.SerializerMethodField(read_only=True)
    # true while the password is a temporary one: no tokens are issued until the
    # user replaces it (POST password/change/temporary/)
    must_change_password = serializers.BooleanField(read_only=True)

    def get_tokens(self, obj):
        return obj["tokens"]

    def validate(self, attrs):
        request = self.context.get("request")

        identifier = attrs.get("identifier", "").strip()
        password = attrs.get("password")

        user = authenticate(
            value=identifier,
            password=password,
        )

        if not user:
            raise AuthenticationFailed(
                Translate.tdc(request, "Invalid credentials")
            )

        if not user.is_active:
            raise AuthenticationFailed(
                Translate.tdc(request, "Account deactivated")
            )

        state = temporary_password_service.state_of(user)

        # An expired temporary password never gets in - and nothing is
        # revealed: an administrator has to issue a new one.
        if state == temporary_password_service.EXPIRED:
            raise AuthenticationFailed({
                "code": "temporary_password_expired",
                "detail": Translate.tdc(request, "The temporary password has expired. Ask an administrator for a new one."),
            })

        # A user WITH an e-mail must have verified it; one without any e-mail
        # (an account provisioned from a Person) has nothing to verify.
        # A temporary password is checked first: its owner has to replace it
        # before anything else, and gets no session until then.
        if state != temporary_password_service.TEMPORARY and user.email and not user.is_verified_email:
            raise AuthenticationFailed(
                Translate.tdc(request, "Email not verified")
            )

        if state == temporary_password_service.TEMPORARY:
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "mobile": user.mobile,
                "must_change_password": True,
                "tokens": None,
            }

        tokens = user.tokens()
        session_service.record_login(user, request, tokens)

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "mobile": user.mobile,
            "must_change_password": False,
            "tokens": tokens,
        }

import jwt

from django.conf import settings

from rest_framework import permissions, status, views
from rest_framework.response import Response

from django_resaas.saas.models.user import User
from django_resaas.saas.data.user.serializers.me import MeSerializer
from django_resaas.saas.core.utils.translate import Translate


class VerifyEmail(views.APIView):
    """
    POST email/verify/  {token}

    PUBLIC (explicit): the signed token is the authorisation. It VERIFIES the
    account's e-mail, so it is POST only (a GET must never change state); the
    token is read from the body, or from the query string for the old contract.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = MeSerializer

    def post(self, request):
        token = request.data.get('token') or request.GET.get('token')

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            user = User.objects.get(id=payload['user_id'])

            # the real field (the old code set `is_verified`, which does not
            # exist, so it reported success without verifying anything)
            if not user.is_verified_email:
                user.is_verified_email = True
                user.save(update_fields=['is_verified_email'])

            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'Account activated successfully'
                    )
                },
                status=status.HTTP_200_OK
            )

        except jwt.ExpiredSignatureError:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Activation expired'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except jwt.exceptions.DecodeError:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Invalid token'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

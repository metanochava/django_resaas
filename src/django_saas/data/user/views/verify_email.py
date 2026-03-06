import jwt

from django.conf import settings

from rest_framework import status, views
from rest_framework.response import Response

from django_saas.models.user import User
from django_saas.data.user.serializers.me import MeSerializer
from django_saas.core.utils.translate import Translate


class VerifyEmail(views.APIView):
    serializer_class = MeSerializer

    def get(self, request):
        token = request.GET.get('token')

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            user = User.objects.get(id=payload['user_id'])

            if not user.is_verified:
                user.is_verified = True
                user.save()

            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'Conta activada com sucesso'
                    )
                },
                status=status.HTTP_200_OK
            )

        except jwt.ExpiredSignatureError:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Activação expirada'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except jwt.exceptions.DecodeError:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Token inválido'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

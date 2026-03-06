import os

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpResponsePermanentRedirect
from django.utils.encoding import smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode

from rest_framework import generics, status
from rest_framework.response import Response

from django_saas.models.user import User
from django_saas.core.utils.translate import Translate


class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = [os.environ.get('APP_SCHEME'), 'http', 'https']


class PasswordTokenCheckAPIView(generics.GenericAPIView):

    def get(self, request, uidb64, token):
        redirect_url = request.GET.get('redirect_url')

        try:
            user_id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                if redirect_url and len(redirect_url) > 3:
                    return CustomRedirect(
                        f'{redirect_url}?token_valid=False'
                    )
                return CustomRedirect(
                    f"{os.environ.get('FRONTEND_URL', '')}?token_valid=False"
                )

            if redirect_url and len(redirect_url) > 3:
                return CustomRedirect(
                    f'{redirect_url}?token_valid=True'
                    f'&message=Credenciais válidas'
                    f'&uidb64={uidb64}&token={token}'
                )

            return CustomRedirect(
                f"{os.environ.get('FRONTEND_URL', '')}?token_valid=False"
            )

        except DjangoUnicodeDecodeError:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'O token não é válido, solicite um novo'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

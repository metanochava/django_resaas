from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils.encoding import smart_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import generics, status
from rest_framework.response import Response

from django_saas.models.user import User
from django_saas.data.user.serializers.request_password_reset_email import (
    ResetPasswordEmailRequestSerializer
)
from django_saas.core.utils.translate import Translate
from django_saas.core.utils.templates import render_email_template


class RequestPasswordResetEmailAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordEmailRequestSerializer

    def post(self, request):
        nome = (
            request.META.get('HTTP_ORIGIN', '')
            .split('.')[0]
            .upper()
            .split('/')[-1]
        )

        serializer = self.serializer_class(data=request.data)
        email = request.data.get('email', '')

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)

            uidb64 = urlsafe_base64_encode(
                smart_bytes(user.id)
            )
            token = PasswordResetTokenGenerator().make_token(user)

            relative_link = reverse(
                'password-reset-confirm',
                kwargs={
                    'uidb64': uidb64,
                    'token': token
                }
            )

            redirect_url = request.data.get('redirect_url', '')

            base_url = request.META.get(
                'HTTP_ORIGIN',
                'http://mws.mytech.co.mz'
            )

            reset_link = (
                f'{base_url}/#/resetpassword'
                f'{relative_link}?redirect_url={redirect_url}'
            )

            html_message = render_email_template(
                'PASSWORD_RESET',
                {
                    'link': reset_link,
                    'username': user.username,
                    'logo': 'logo',
                }
            )

            try:
                mail = EmailMultiAlternatives(
                    subject=Translate.tdc(
                        request,
                        'Redefinição de palavra-passe'
                    ),
                    body='',
                    to=[email],
                )
                mail.attach_alternative(
                    html_message,
                    'text/html'
                )
                mail.send()

            except Exception:
                return Response(
                    {
                        'alert_error': Translate.tdc(
                            request,
                            'Erro ao enviar o email'
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'Enviámos um link para redefinir a sua palavra-passe'
                )
            },
            status=status.HTTP_200_OK
        )

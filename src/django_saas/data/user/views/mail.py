from django.conf import settings
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


class MailAPIView(generics.GenericAPIView):
    """
    Envio de email genérico para redefinição de palavra-passe.
    Responsabilidade única: gerar link e enviar email HTML.
    """
    serializer_class = ResetPasswordEmailRequestSerializer

    def get(self, request):
        email = request.query_params.get('email')

        if not email:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Email não informado'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not User.objects.filter(email=email).exists():
            # Resposta neutra por segurança
            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'Se o email existir, enviaremos instruções'
                    )
                },
                status=status.HTTP_200_OK
            )

        user = User.objects.get(email=email)

        uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
        token = PasswordResetTokenGenerator().make_token(user)

        relative_link = reverse(
            'password-reset-confirm',
            kwargs={
                'uidb64': uidb64,
                'token': token,
            }
        )

        redirect_url = request.GET.get('redirect_url', '')

        base_url = request.META.get(
            'HTTP_ORIGIN',
            settings.FRONTEND_URL
        )

        reset_link = (
            f'{base_url}/#/resetpassword{relative_link}'
            f'?redirect_url={redirect_url}'
        )

        html_message = render_email_template(
            'GENERIC_RESET',
            {
                'username': user.username,
                'link': reset_link,
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

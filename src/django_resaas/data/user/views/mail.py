from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils.encoding import smart_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import generics, status
from rest_framework.response import Response

from django_resaas.models.user import User
from django_resaas.data.user.serializers.request_password_reset_email import (
    ResetPasswordEmailRequestSerializer
)
from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils.templates import render_email_template


class MailAPIView(generics.GenericAPIView):
    """
    Generic email sending for password reset.
    Single responsibility: generate the link and send the HTML email.
    """
    serializer_class = ResetPasswordEmailRequestSerializer

    def get(self, request):
        email = request.query_params.get('email')

        if not email:
            return Response(
                {
                    'alert_error': Translate.tdc(
                        request,
                        'Email not provided'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not User.objects.filter(email=email).exists():
            # Neutral response for security
            return Response(
                {
                    'alert_success': Translate.tdc(
                        request,
                        'If the email exists, we will send instructions'
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
                    'Password reset'
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
                        'Error sending the email'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                'alert_success': Translate.tdc(
                    request,
                    'We sent a link to reset your password'
                )
            },
            status=status.HTTP_200_OK
        )

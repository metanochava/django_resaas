from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import smart_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import generics, status
from rest_framework.response import Response

from django_resaas.engine.models.user import User
from django_resaas.engine.data.user.serializers.request_password_reset_email import (
    ResetPasswordEmailRequestSerializer
)
from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.core.utils.templates import render_email_template


class RequestPasswordResetEmailAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordEmailRequestSerializer

    def post(self, request):
        name = (
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

            redirect_url = request.data.get('redirect_url', '')

            base_url = request.META.get(
                'HTTP_ORIGIN',
                'http://mws.mytech.co.mz'
            )

            # Points straight at a frontend route (SPA hash routing) -
            # no backend reverse() involved, so there's no URL name to
            # keep in sync between the two.
            reset_link = (
                f'{base_url}/#/resetpassword/{uidb64}/{token}'
                f'?redirect_url={redirect_url}'
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

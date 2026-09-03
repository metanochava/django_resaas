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
from django_resaas.engine.core.utils.email_branding import resolve_email_branding


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

            entity_name, logo_url = resolve_email_branding(request)

            html_message = render_email_template(
                'PASSWORD_RESET',
                {
                    'link': reset_link,
                    'entity_name': entity_name,
                    'logo': logo_url,
                    'greeting': Translate.tdc(request, 'Hi {username},').format(
                        username=user.username
                    ),
                    'intro': Translate.tdc(
                        request,
                        'We received a request to reset your password. '
                        'Click the button below to choose a new one.'
                    ),
                    'button_label': Translate.tdc(request, 'Reset password'),
                    'ignore_notice': Translate.tdc(
                        request, "If you didn't request this, you can safely ignore this email."
                    ),
                    'footer_notice': Translate.tdc(
                        request, 'This is an automated message, please do not reply.'
                    ),
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

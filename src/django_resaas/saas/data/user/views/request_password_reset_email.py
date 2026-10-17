from django.core.mail import EmailMultiAlternatives

from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django_resaas.saas.models.user import User
from django_resaas.saas.data.user.serializers.request_password_reset_email import (
    ResetPasswordEmailRequestSerializer
)
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.core.utils.templates import render_email_template
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.core.exceptions import error_response
from django_resaas.saas.core.services.password_reset_service import (
    ResetLinkUnavailable, link_available, reset_link as build_reset_link,
)


class RequestPasswordResetEmailAPIView(ResaasResponseMixin, generics.GenericAPIView):

    # PUBLIC (explicit): used before there is a session
    permission_classes = (permissions.AllowAny,)
    serializer_class = ResetPasswordEmailRequestSerializer

    def post(self, request):
        name = (
            request.META.get('HTTP_ORIGIN', '')
            .split('.')[0]
            .upper()
            .split('/')[-1]
        )

        return self.send_reset_email(request, request.data.get('email', ''))

    def send_reset_email(self, request, email):
        """The whole flow for one address (shared with the deprecated
        MailAPIView): trusted origin only, same answer whether the account
        exists or not."""
        # before the lookup: the answer must not depend on the account existing
        if not link_available(request):
            return error_response(
                request,
                "The reset link cannot be sent from this address. Ask for a code instead.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
                code="reset_link_unavailable",
            )

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)

            # a trusted frontend origin only (CORS policy / FRONTEND_URL),
            # on the real route /#/auth/resetpassword/<uidb64>/<token>
            try:
                reset_link = build_reset_link(request, user)
            except ResetLinkUnavailable:
                return error_response(
                    request,
                    "The reset link cannot be sent from this address. Ask for a code instead.",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="reset_link_unavailable",
                )

            html_message = render_email_template(
                'PASSWORD_RESET',
                {
                    'link': reset_link,
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
                },
                request=request,
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

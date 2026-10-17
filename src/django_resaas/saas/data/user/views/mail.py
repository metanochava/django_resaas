from django.core.mail import EmailMultiAlternatives  # noqa: F401 (tests patch it here)

from rest_framework import permissions, status
from rest_framework.response import Response

from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.data.user.views.request_password_reset_email import RequestPasswordResetEmailAPIView


class MailAPIView(RequestPasswordResetEmailAPIView):
    """
    POST mail/  {email}   (DEPRECATED - use POST password/reset/email/)

    PUBLIC (explicit): a password reset is requested before signing in. It
    SENDS an email, so it is POST only - a GET must never have side effects
    (link prefetchers and crawlers would trigger it). `email` is read from the
    body, or from the query string for callers of the old GET contract.

    It is an alias of password/reset/email/ (same flow, same answers). It
    used to build the link from the raw Origin header (anyone could have a
    real reset token mailed to a victim pointing at their own host) on a URL
    name that does not exist (500 for every real account, 200 for unknown
    ones - telling which addresses have an account).
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.data.get('email') or request.query_params.get('email')

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

        return self.send_reset_email(request, email)

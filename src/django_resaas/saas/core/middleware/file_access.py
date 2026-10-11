import posixpath
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse, JsonResponse

from rest_framework import status

from django_resaas.saas.core.conf import get_setting
from django_resaas.saas.core.exceptions.handler import error_body
from django_resaas.saas.core.utils.full_path import FullPath
from django_resaas.saas.core.utils.translate import Translate


class FileAccessMiddleware:
    """Every MEDIA_URL request needs a token issued for that exact path
    (FullPath.url). Without one the answer is 401.

    With FILE_TOKEN.X_ACCEL_REDIRECT set (e.g. "/protected-media/") a valid
    request is answered with an X-Accel-Redirect to that internal nginx
    location, so nginx sends the file after Django has checked the token.
    Without it the request goes on to the view that serves media (Django's
    static() in DEBUG)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if not request.path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        token = request.GET.get('token')
        relative = posixpath.normpath(request.path[len(settings.MEDIA_URL):])

        if not token or relative.startswith(('..', '/')) or not FullPath.validate_token(token, request.path):
            return JsonResponse(
                error_body(Translate.tdc(request, 'Not authorized'), code='file_token_invalid'),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        internal = get_setting('FILE_TOKEN.X_ACCEL_REDIRECT')
        if internal:
            response = HttpResponse()
            # nginx takes the type from the file it serves
            del response['Content-Type']
            response['X-Accel-Redirect'] = internal.rstrip('/') + '/' + quote(relative)
            return response

        return self.get_response(request)

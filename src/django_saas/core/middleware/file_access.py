from django.conf import settings
from django.http import JsonResponse

from rest_framework import status

from django_saas.core.utils.full_path import FullPath
from django_saas.core.utils.translate import Translate



class FileAccessMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith(settings.MEDIA_URL):

            token = request.GET.get('token')

            if token and FullPath.validate_token(token):
                return self.get_response(request)

            return JsonResponse(
                {
                    'alert_error': Translate.tdc(request, 'Nao autorizado')
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        return self.get_response(request)




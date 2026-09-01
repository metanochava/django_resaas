from django.http import JsonResponse

from rest_framework import status

from django_resaas.models.front_end import FrontEnd
from django_resaas.core.utils.translate import Translate
from django_resaas.core.conf import get_setting



class FrontEndMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path
        scope = self.get_url_scope(path)

        # URLs públicas globais
        if scope in get_setting('FRONT_END.PUBLIC_URL', []):
            return self.get_response(request)

        if str(get_setting('FRONT_END.REQUIRE_CREDENTIALS')).lower() in ['true', '1', 'yes']:

            fek = request.headers.get('FEK')
            fep = request.headers.get('FEP')

            if not fek or not fep:
                return self._unauthorized('Not authorized')

            frontend = FrontEnd.objects.filter(fek=fek, fep=fep).first()

            if not frontend:
                return self._unauthorized('Bad Credentials')

            # guardar no request
            request.frontend = frontend

            # 🔐 validar URL
            if not self._has_url_permission(frontend, scope):
                return self._forbidden('No permission for this route')

            # 🔐 validar método HTTP
            if not self._has_method_permission(frontend, request.method):
                return self._forbidden('No permission for this operation')

        return self.get_response(request)

    # --------------------
    # Helpers
    # --------------------

    def get_url_scope(self, path):
        parts = path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'api':
            return parts[1]
        return None

    def _has_url_permission(self, frontend, scope):
        rules = get_setting('FRONT_END.URL_RULES', {})

        if not scope or scope not in rules:
            # No rule defined for this scope. Historically this always
            # allowed the request through; that is preserved as the
            # default ('allow') for backward compatibility, but a
            # deployment can opt into fail-closed behavior by setting
            # FRONT_END.DEFAULT_POLICY = 'deny'.
            policy = str(get_setting('FRONT_END.DEFAULT_POLICY', 'allow')).lower()
            return policy != 'deny'

        return frontend.access in rules[scope]

    def _has_method_permission(self, frontend, method):
        method = method.upper()

        if frontend.access == 'super':
            return True  # 🔥 tudo permitido

        if frontend.access == 'read':
            return method in ['GET', 'HEAD', 'OPTIONS']

        if frontend.access == 'readwrite':
            # readwrite is a superset of both read and write, so it must
            # allow everything write allows too - DELETE included.
            return method in ['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE']

        if frontend.access == 'write':
            return method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']

        return False

    def _unauthorized(self, msg):
        return JsonResponse(
            {
                'code': 10001,
                'alert_error': Translate.tdc(None, msg)
            },
            status=status.HTTP_401_UNAUTHORIZED
        )

    def _forbidden(self, msg):
        return JsonResponse(
            {
                'code': 10003,
                'alert_error': Translate.tdc(None, msg)
            },
            status=status.HTTP_403_FORBIDDEN
        )


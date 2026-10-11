import time
import hmac
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, unquote

from django.utils.crypto import constant_time_compare


class FullPath:
    """
    Geração e validação de URLs protegidas para files.

    A token is signed over its expiry AND the file path it was issued for, so
    a token from one URL never opens another file (a permanent token used to
    be a master key for every file of the server).
    """

    # -------------------------
    # TOKEN CORE
    # -------------------------


    @staticmethod
    def _signature(key, payload, path):
        message = f'{payload}:{unquote(path or "")}'
        return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _generate_token(path, expire_at=0):
        from django_resaas.saas.core.conf import get_setting  # lazy import

        key = get_setting('FILE_TOKEN.KEY')
        if not key:
            return None

        payload = str(expire_at)
        return f'{payload}.{FullPath._signature(key, payload, path)}'

    # -------------------------
    # PUBLIC API
    # -------------------------

    @staticmethod
    def generate_permanent_token(path):
        from django_resaas.saas.core.conf import get_setting  # lazy import

        if not get_setting('FILE_TOKEN.ENABLE_PERMANENT'):
            return None
        return FullPath._generate_token(path, 0)

    @staticmethod
    def generate_temporary_token(path):
        from django_resaas.saas.core.conf import get_setting  # lazy import

        if not get_setting('FILE_TOKEN.ENABLE_TEMPORARY'):
            return None

        ttl = int(get_setting('FILE_TOKEN.TEMP_TTL', 300))
        expire_at = int(time.time()) + ttl
        return FullPath._generate_token(path, expire_at)

    @staticmethod
    def validate_token(token, path):
        """True when token was issued for this URL path (e.g. request.path)
        and has not expired."""
        from django_resaas.saas.core.conf import get_setting  # lazy import

        try:
            payload, signature = token.split('.')
            expire_at = int(payload)
        except ValueError:
            return False

        key = get_setting('FILE_TOKEN.KEY')
        if not key:
            return False

        if not constant_time_compare(signature, FullPath._signature(key, payload, path)):
            return False

        if expire_at and time.time() > expire_at:
            return False

        return True

    # -------------------------
    # URL BUILDER
    # -------------------------

    @staticmethod
    def url(request, file_url, temporary=True):
        """
        Gera URL protegida para FileField / ImageField.

        Aceita:
        - instance.file.url
        - path relativo
        - URL absoluta
        """

        if not file_url:
            return None

        parsed = urlparse(file_url)

        # URL absoluta
        if parsed.scheme and parsed.netloc:
            base_url = file_url
        else:
            if not request:
                return None
            base_url = request.build_absolute_uri(file_url)

        parsed = urlparse(base_url)

        token = (
            FullPath.generate_temporary_token(parsed.path)
            if temporary
            else FullPath.generate_permanent_token(parsed.path)
        )

        if not token:
            return None

        query = parse_qs(parsed.query)
        query['token'] = token

        return urlunparse(
            parsed._replace(query=urlencode(query, doseq=True))
        )

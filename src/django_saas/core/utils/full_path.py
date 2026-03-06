import time
import hmac
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from django.utils.crypto import constant_time_compare


class FullPath:
    """
    Geração e validação de URLs protegidas para ficheiros.
    """

    # -------------------------
    # TOKEN CORE
    # -------------------------


    @staticmethod
    def _generate_token(expire_at=0):
        from django_saas.core.conf import get_setting  # lazy import

        key = get_setting('FILE_TOKEN.KEY')
        if not key:
            return None

        payload = str(expire_at)
        signature = hmac.new(
            key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return f'{payload}.{signature}'

    # -------------------------
    # PUBLIC API
    # -------------------------

    @staticmethod
    def generate_permanent_token():
        from django_saas.core.conf import get_setting  # lazy import

        if not get_setting('FILE_TOKEN.ENABLE_PERMANENT'):
            return None
        return FullPath._generate_token(0)

    @staticmethod
    def generate_temporary_token():
        from django_saas.core.conf import get_setting  # lazy import

        if not get_setting('FILE_TOKEN.ENABLE_TEMPORARY'):
            return None

        ttl = int(get_setting('FILE_TOKEN.TEMP_TTL', 300))
        expire_at = int(time.time()) + ttl
        return FullPath._generate_token(expire_at)

    @staticmethod
    def validate_token(token):
        from django_saas.core.conf import get_setting  # lazy import

        try:
            payload, signature = token.split('.')
        except ValueError:
            return False

        key = get_setting('FILE_TOKEN.KEY')
        if not key:
            return False

        expected = hmac.new(
            key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        if not constant_time_compare(signature, expected):
            return False

        expire_at = int(payload)
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

        token = (
            FullPath.generate_temporary_token()
            if temporary
            else FullPath.generate_permanent_token()
        )

        if not token:
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
        query = parse_qs(parsed.query)
        query['token'] = token

        return urlunparse(
            parsed._replace(query=urlencode(query, doseq=True))
        )

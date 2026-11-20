"""Verifying a printed document: its QR code is a link to a public page that
says whether this system issued it and what it is now (paid, voided...).

The link carries a signed token - {document code, object id} signed with the
SECRET_KEY (django.core.signing, like the tenant context): it cannot be
guessed nor altered, and it does not expire (a receipt is valid for years).
Whoever reads it needs no session; the page shows only the document's public
fields (its "verify" callable) - never a customer's data."""
from urllib.parse import urlparse

from django.conf import settings
from django.core import signing

SALT = "resaas.print.verify"


def make_token(document_code, obj):
    return signing.dumps({"d": document_code, "o": str(obj.pk)}, salt=SALT, compress=True)


def read_token(token):
    """(document_code, object_id), or None when the token is not ours."""
    try:
        payload = signing.loads(str(token or ""), salt=SALT)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict) or not payload.get("d") or not payload.get("o"):
        return None
    return payload["d"], payload["o"]


def _allowed_origin(origin):
    """An origin the API already trusts (CORS: the list, the regexes, the
    CorsAllowedOrigin rows) - never an arbitrary one."""
    import re

    from django_resaas.saas.core.utils.cors_allowed_origin import get_cors_origins

    allowed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []) or []) | set(get_cors_origins() or [])
    if origin in allowed:
        return True
    return any(re.match(pattern, origin) for pattern in getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", []) or [])


def verify_base(request):
    """Where the verification page lives: the frontend that asked for the PDF
    (its Origin, when it is an allowed one), else settings.RESAAS_VERIFY_URL."""
    origin = (request.headers.get("Origin") if request is not None else None) or ""
    if origin and urlparse(origin).scheme in ("http", "https") and _allowed_origin(origin):
        return origin.rstrip("/")
    return str(getattr(settings, "RESAAS_VERIFY_URL", "") or "").rstrip("/")


def verify_url(request, document_code, obj):
    base = verify_base(request)
    token = make_token(document_code, obj)
    # hash routing: works with both router modes of the frontend
    return f"{base}/#/v/{token}" if base else None

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


ISSUE = "@issue"


def read_payload(token):
    """The signed payload, or None when the token is not ours."""
    try:
        payload = signing.loads(str(token or ""), salt=SALT)
    except signing.BadSignature:
        return None
    return payload if isinstance(payload, dict) and payload.get("d") else None


def read_token(token):
    """(document_code, object_id) of a registered document, or None."""
    payload = read_payload(token)
    if not payload or payload["d"] == ISSUE or not payload.get("o"):
        return None
    return payload["d"], payload["o"]


def make_issue_token(subject, entity_id=None, branch_id=None, obj=None):
    """Any PDF (core/utils PDF()): what it is, who issued it and when - and,
    when it is about one record, that record (so the page can say whether it
    still stands). Signed, so only documents this system produced verify."""
    from django.utils import timezone

    payload = {"d": ISSUE, "s": str(subject or "")[:120], "t": timezone.now().isoformat(timespec="minutes")}
    if entity_id:
        payload["e"] = str(entity_id)
    if branch_id:
        payload["b"] = str(branch_id)
    if obj is not None and getattr(obj, "pk", None) is not None:
        payload["m"] = obj._meta.label_lower
        payload["o"] = str(obj.pk)
    return signing.dumps(payload, salt=SALT, compress=True)


def _allowed_origin(origin):
    """An origin the API already trusts (CORS: the list, the regexes, the
    CorsAllowedOrigin rows) - never an arbitrary one."""
    import re

    from django_resaas.saas.core.utils.cors_allowed_origin import get_cors_origins

    allowed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []) or []) | set(get_cors_origins() or [])
    if origin in allowed:
        return True
    return any(re.match(pattern, origin) for pattern in getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", []) or [])


def _origin_of(url):
    parsed = urlparse(str(url or ""))
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def verify_base(request):
    """Where the verification page lives: the frontend that asked for the PDF,
    when the API already trusts it (CORS) - its Origin (a cross-origin call),
    else its Referer (a same-origin call through the site's /api/ proxy sends
    no Origin), else the request's own host (that proxy) - and last
    settings.RESAAS_VERIFY_URL."""
    if request is not None:
        sent = request.headers.get("Origin")
        if sent:
            # a cross-origin call: that frontend, or none
            candidates = [sent]
        else:
            # same origin (the site proxies /api/): the page's own address
            candidates = [request.headers.get("Referer")]
            try:
                candidates.append(f"https://{request.get_host()}")
            except Exception:
                pass
        for origin in candidates:
            origin = _origin_of(origin)
            if origin and _allowed_origin(origin):
                return origin.rstrip("/")
    return str(getattr(settings, "RESAAS_VERIFY_URL", "") or "").rstrip("/")


def verify_url(request, document_code, obj):
    base = verify_base(request)
    token = make_token(document_code, obj)
    # hash routing: works with both router modes of the frontend
    return f"{base}/#/v/{token}" if base else None


def issue_url(request, subject, obj=None):
    base = verify_base(request)
    if not base:
        return None
    token = make_issue_token(subject, getattr(request, "entity_id", None), getattr(request, "branch_id", None), obj)
    return f"{base}/#/v/{token}"

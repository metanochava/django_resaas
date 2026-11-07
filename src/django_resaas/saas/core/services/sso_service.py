"""
Single sign-on between the frontend domains of one deployment.

A domain that has a session asks for a short single-use CODE for another
domain (`issue_code`), the browser carries it there in a top-level redirect,
and that domain exchanges it for its OWN session (`redeem`) - an authorization
code with PKCE (S256), reduced to what RESAAS needs. No token ever travels in
a URL, and no cookie is shared between domains.

Rules:
- the code is issued only from a full session (the password step, two-factor
  and a temporary-password change are already behind any access token);
- `redirect_uri` must belong to an origin the CORS policy trusts
  (CORS_ALLOWED_ORIGINS / CORS_ALLOWED_ORIGIN_REGEXES - the frontends that may
  call this API), so there is no open redirect;
- the code lives CODE_TTL seconds, is stored only as a keyed hash, is bound to
  its redirect_uri and PKCE challenge, and works once (row lock + used_at);
- redeeming it mints a new session (refresh token + UserLogin) on the target
  domain, listed and ended like any other session. Tenant context (Entity,
  Branch, Group) is NOT carried: each domain chooses and validates its own;
- sessions started from one another share a family (session_service), and
  signing out (`sign_out`) ends the whole family: no domain of that browser
  signs itself in again. Sessions on other devices are not touched.
"""
import base64
import hashlib
import re
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from django_resaas.saas.core.services import audit_service, session_service
from django_resaas.saas.core.services.app_manifest_service import cors_allows_origin
from django_resaas.saas.models.sso_authorization_code import SsoAuthorizationCode

CODE_TTL = 60  # seconds
HASH_SALT = "resaas.sso.code"
SIGN_IN = "SSO_SIGN_IN"
SIGN_OUT = "SSO_SIGN_OUT"

# RFC 7636: the S256 challenge is base64url(sha256(verifier)) without padding
# (43 chars); the verifier is 43-128 unreserved characters
_CHALLENGE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_VERIFIER = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")


class SsoError(Exception):
    def __init__(self, code, message, http_status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _hash(code):
    return salted_hmac(HASH_SALT, code, algorithm="sha256").hexdigest()


def challenge_for(verifier):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def redirect_origin(redirect_uri):
    """The origin of a redirect_uri, or None when it is not a plain
    http(s) URL (no credentials in it)."""
    try:
        parts = urlsplit(redirect_uri or "")
    except ValueError:
        return None
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def allowed_redirect(redirect_uri):
    origin = redirect_origin(redirect_uri)
    return bool(origin) and len(redirect_uri) <= 500 and cors_allows_origin(origin)


def issue_code(user, redirect_uri, code_challenge, request=None):
    """A new single-use code for `redirect_uri`; returns the code in clear
    (only its hash is stored)."""
    if not isinstance(redirect_uri, str) or not allowed_redirect(redirect_uri):
        raise SsoError("sso_invalid_redirect", "This site is not allowed to use the shared sign-in.")
    if not isinstance(code_challenge, str) or not _CHALLENGE.match(code_challenge):
        raise SsoError("sso_invalid_request", "The sign-in request is not valid.")

    source_jti = session_service.current_session_id(request) or ""
    # an access token outlives its session by a few minutes: a session that
    # was signed out of never starts another one
    if session_service.session_ended(source_jti):
        raise SsoError("sso_session_ended", "Your session has ended. Sign in again.", 401)

    now = timezone.now()
    # spent and expired codes of this user have no use left
    SsoAuthorizationCode.objects.filter(user=user, expires_at__lt=now).delete()

    code = secrets.token_urlsafe(32)
    SsoAuthorizationCode.objects.create(
        user=user,
        code_hash=_hash(code),
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        source_jti=source_jti,
        expires_at=now + timedelta(seconds=CODE_TTL),
    )
    return code


def redeem(code, code_verifier, redirect_uri, request=None):
    """Spend a code; returns (user, source_jti) - the caller mints the new
    session in the family of `source_jti` (`family_for`). Every failure is the
    same answer, so nothing is learned about a code."""
    invalid = SsoError("sso_code_invalid", "This sign-in link is no longer valid. Sign in again.", 401)

    if not all(isinstance(value, str) for value in (code, code_verifier, redirect_uri)):
        raise invalid
    if not code or not _VERIFIER.match(code_verifier):
        raise invalid

    with transaction.atomic():
        row = (
            SsoAuthorizationCode.objects.select_for_update()
            .select_related("user")
            .filter(code_hash=_hash(code))
            .first()
        )
        if row is None or row.used_at is not None or row.expires_at <= timezone.now():
            raise invalid

        # spent on the first presentation, whatever comes next: the checks
        # below only decide the answer, so the commit must not depend on them
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])

        valid = (
            constant_time_compare(row.redirect_uri, redirect_uri)
            and constant_time_compare(row.code_challenge, challenge_for(code_verifier))
            and row.user.is_active
            and not session_service.session_ended(row.source_jti)
        )

    if not valid:
        raise invalid

    audit_service.record(
        action=SIGN_IN,
        target=row.user,
        actor=row.user,
        request=request,
        details={"origin": redirect_origin(redirect_uri)},
    )
    return row.user, row.source_jti


def previous_session(user, refresh):
    """The jti of `refresh` when it is a live session of `user` (the session
    a domain had before adopting another one), else None. Never fails."""
    if not isinstance(refresh, str) or not refresh:
        return None

    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.settings import api_settings
    from rest_framework_simplejwt.tokens import RefreshToken

    try:
        token = RefreshToken(refresh)  # signature, expiry and blacklist
    except TokenError:
        return None

    if str(token.get(api_settings.USER_ID_CLAIM)) != str(getattr(user, api_settings.USER_ID_FIELD)):
        return None
    return token.get("jti")


def sign_out(user, request):
    """End the request's session and every session of its single sign-on
    family; returns how many were ended."""
    jti = session_service.current_session_id(request)
    if not jti:
        return 0

    ended = session_service.terminate_sso_family(user, jti)
    audit_service.record(action=SIGN_OUT, target=user, actor=user, request=request, details={"ended": ended})
    return ended

"""The refresh token in an HttpOnly cookie, for the frontends of the API's own
site (docs/security/sessions-and-tokens.md, phase 2).

A frontend on the same registrable site as the API (settings
RESAAS_REFRESH_COOKIE_SITES, e.g. ["mytech.co.mz"]: venda.mytech.co.mz and
app.mytech.co.mz) never sees its refresh token:

- every answer that carries one (login, two-factor, the temporary password
  change, single sign-on, registration, refresh) sets it in the cookie
  instead and drops it from the body; the body says until when the cookie
  lives (`refresh_cookie.expires_at`);
- the refresh, logout and single sign-on endpoints read it from the cookie
  when the body has none;
- the sign-out endpoints clear it.

Any other frontend (an own domain: clinicaamal.co.mz) keeps the refresh token
in the body - there the cookie would be a third-party one the browsers block.

The cookie: HttpOnly (no script reads it), Secure, SameSite=Lax (another site
never sends it), Path = the API prefix. It is read only when the request's
Origin is one of the cookie sites - the CSRF guard of a cookie-authenticated
POST (SameSite=Lax already keeps other sites' requests out).
"""
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone


def _setting(name, default):
    return getattr(settings, name, default)


def cookie_name():
    return _setting("RESAAS_REFRESH_COOKIE_NAME", "resaas_refresh")


def cookie_path():
    return _setting("RESAAS_REFRESH_COOKIE_PATH", "/api/")


def cookie_sites():
    return [str(site).lower().strip(".") for site in _setting("RESAAS_REFRESH_COOKIE_SITES", []) or [] if site]


def _within(host, site):
    host = (host or "").lower()
    return host == site or host.endswith("." + site)


def cookie_mode(request):
    """The request comes from a frontend of the API's own site: its refresh
    token belongs in the cookie."""
    origin = request.headers.get("Origin") if request is not None else None
    if not origin:
        return False
    origin_host = urlparse(origin).hostname or ""
    api_host = (request.get_host() or "").split(":")[0]
    return any(_within(origin_host, site) and _within(api_host, site) for site in cookie_sites())


def read(request):
    """The refresh token of the cookie, only for a request of a cookie site
    (else None)."""
    if not cookie_mode(request):
        return None
    return request.COOKIES.get(cookie_name()) or None


def _lifetime():
    from rest_framework_simplejwt.settings import api_settings

    return api_settings.REFRESH_TOKEN_LIFETIME


def set_cookie(response, refresh):
    lifetime = _lifetime()
    response.set_cookie(
        cookie_name(), refresh,
        max_age=int(lifetime.total_seconds()),
        path=cookie_path(),
        secure=_setting("RESAAS_REFRESH_COOKIE_SECURE", True),
        httponly=True,
        samesite="Lax",
    )
    return timezone.now() + lifetime


def clear(response):
    response.delete_cookie(cookie_name(), path=cookie_path(), samesite="Lax")


def apply(request, response):
    """Move an answer's refresh token into the cookie (cookie sites only):
    `{"tokens": {"refresh"}}` (login and the like) or `{"refresh", "access"}`
    (the refresh endpoint). The body then says until when the cookie lives."""
    data = getattr(response, "data", None)
    if not isinstance(data, dict) or response.status_code >= 400 or not cookie_mode(request):
        return
    tokens = data.get("tokens")
    if isinstance(tokens, dict) and tokens.get("refresh"):
        refresh = tokens["refresh"]
        data = {**data, "tokens": {k: v for k, v in tokens.items() if k != "refresh"}}
    elif data.get("refresh") and data.get("access"):
        refresh = data["refresh"]
        data = {k: v for k, v in data.items() if k != "refresh"}
    else:
        return
    expires_at = set_cookie(response, refresh)
    data["refresh_cookie"] = {"expires_at": expires_at.isoformat()}
    response.data = data

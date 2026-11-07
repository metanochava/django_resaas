"""
The signed-in sessions of a user, from what already exists: every sign-in mints
a refresh token (an OutstandingToken row) and records a UserLogin with that
token's jti and the device. A session is ACTIVE while its refresh token is
neither blacklisted nor expired; ending it blacklists the token (no new access
tokens can be minted - an access token already issued lives out its few
minutes). Nothing about location is inferred (no IP geolocation) - only what the
browser itself sent (its user agent).
"""
import re
import uuid

from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from django_resaas.saas.models.user_login import UserLogin

_BROWSERS = (
    ("Edge", r"Edg(?:e|A|iOS)?/"),
    ("Opera", r"OPR/|Opera"),
    ("Firefox", r"Firefox/|FxiOS/"),
    ("Chrome", r"Chrome/|CriOS/"),
    ("Safari", r"Safari/"),
)

_SYSTEMS = (
    ("Windows", r"Windows"),
    ("Android", r"Android"),
    ("iOS", r"iPhone|iPad|iPod"),
    ("macOS", r"Mac OS X|Macintosh"),
    ("Linux", r"Linux|X11"),
)


def describe_device(user_agent):
    """'Chrome · macOS' from a User-Agent string ('' when unknown)."""
    agent = str(user_agent or "")

    browser = next((name for name, pattern in _BROWSERS if re.search(pattern, agent)), "")
    system = next((name for name, pattern in _SYSTEMS if re.search(pattern, agent)), "")

    return " · ".join(part for part in (browser, system) if part)


def record_login(user, request, tokens, sso_family=None):
    """Remember this sign-in: who, when, on what device, and which session
    (`sso_family`: the single sign-on family it joins, if any)."""
    agent = request.META.get("HTTP_USER_AGENT", "") if request is not None else ""

    return UserLogin.objects.create(
        user=user,
        dispositivo=describe_device(agent),
        info=agent[:500],
        token_jti=RefreshToken(tokens["refresh"])["jti"],
        sso_family=sso_family,
    )


def current_session_id(request):
    """The session of the request (None for tokens issued before sessions)."""
    token = getattr(request, "auth", None)

    try:
        return token["sid"] if token is not None and "sid" in token else None
    except (TypeError, KeyError):
        return None


def _active_tokens(user):
    return (
        OutstandingToken.objects
        .filter(user=user, expires_at__gt=timezone.now())
        .exclude(blacklistedtoken__isnull=False)
    )


def active_sessions(user, current_sid=None):
    tokens = {token.jti: token for token in _active_tokens(user)}

    logins = (
        UserLogin.objects
        .filter(user=user, token_jti__in=list(tokens))
        .order_by("-created_at")
    )

    return [
        {
            "id": login.token_jti,
            "device": login.dispositivo or "",
            "created_at": login.created_at,
            "expires_at": tokens[login.token_jti].expires_at,
            "current": bool(current_sid) and login.token_jti == current_sid,
        }
        for login in logins
    ]


def terminate(user, jti):
    """End ONE of the user's own sessions. False when it is not theirs/active."""
    token = _active_tokens(user).filter(jti=jti).first()

    if token is None:
        return False

    BlacklistedToken.objects.get_or_create(token=token)
    return True


def terminate_others(user, current_sid):
    """End every session except the current one; returns how many."""
    count = 0

    for token in _active_tokens(user).exclude(jti=current_sid):
        BlacklistedToken.objects.get_or_create(token=token)
        count += 1

    return count


# ---------------------------------------------------------------- single sign-on
# Sessions started from one another by single sign-on (one browser, several
# domains) share a family id on their UserLogin rows, so signing out on any of
# those domains ends all of them - never the user's sessions on other devices.

def sso_family_of(user, jti):
    """The family of session `jti` (given one when it had none yet); a new id
    when the session is unknown (a token issued before sessions)."""
    login = UserLogin.objects.filter(user=user, token_jti=jti).first() if jti else None

    if login is None:
        return uuid.uuid4()

    if login.sso_family is None:
        login.sso_family = uuid.uuid4()
        login.save(update_fields=["sso_family"])

    return login.sso_family


def join_sso_family(user, family, jti):
    """Bring session `jti` - and its whole family - into `family`."""
    login = UserLogin.objects.filter(user=user, token_jti=jti).first()

    if login is None or login.sso_family == family:
        return

    if login.sso_family is None:
        UserLogin.objects.filter(pk=login.pk).update(sso_family=family)
    else:
        UserLogin.objects.filter(user=user, sso_family=login.sso_family).update(sso_family=family)


def terminate_sso_family(user, jti):
    """End session `jti` and every session of its family; returns how many."""
    login = UserLogin.objects.filter(user=user, token_jti=jti).first()

    if login is None or login.sso_family is None:
        return int(terminate(user, jti))

    jtis = UserLogin.objects.filter(user=user, sso_family=login.sso_family).values_list("token_jti", flat=True)
    count = 0

    for token in _active_tokens(user).filter(jti__in=list(jtis)):
        BlacklistedToken.objects.get_or_create(token=token)
        count += 1

    return count


def session_ended(jti):
    """Whether session `jti` has been ended (its refresh token blacklisted)."""
    return bool(jti) and BlacklistedToken.objects.filter(token__jti=jti).exists()

"""
The signed-in sessions of a user, from what already exists: every sign-in mints
a refresh token (an OutstandingToken row) and records a UserLogin with that
token's jti - the session id, the tokens' "sid" claim - and the device.

The refresh token ROTATES: each refresh returns a new one and blacklists the
one used (SIMPLE_JWT ROTATE_REFRESH_TOKENS / BLACKLIST_AFTER_ROTATION); the
session's id stays (simplejwt keeps the "sid" claim) and UserLogin.current_jti
follows the current token (rotated()). A session is ACTIVE while its current
refresh token is neither blacklisted nor expired; ending it blacklists that
token (no new access tokens can be minted - an access token already issued
lives out its few minutes). A refresh token used again after it was rotated
is taken as stolen: its whole session family ends (refresh_reused()). Nothing about location is inferred (no IP geolocation) - only what the
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
        current_jti=RefreshToken(tokens["refresh"])["jti"],
        sso_family=sso_family,
    )


def _current(login):
    """The jti of a session's current refresh token."""
    return login.current_jti or login.token_jti


def _current_jti_of(user, sid):
    """The current refresh jti of session `sid` (sid itself for a token
    issued before sessions were recorded)."""
    login = UserLogin.objects.filter(user=user, token_jti=sid).first() if sid else None
    return _current(login) if login else sid


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
    """The user's active sessions; "id" is the session id (sid)."""
    from django.db.models import Q

    tokens = {token.jti: token for token in _active_tokens(user)}

    logins = (
        UserLogin.objects
        .filter(user=user)
        .filter(Q(current_jti__in=list(tokens)) | Q(current_jti__isnull=True, token_jti__in=list(tokens)))
        .order_by("-created_at")
    )

    return [
        {
            "id": login.token_jti,
            "device": login.dispositivo or "",
            "created_at": login.created_at,
            "expires_at": tokens[_current(login)].expires_at,
            "current": bool(current_sid) and login.token_jti == current_sid,
        }
        for login in logins
    ]


def terminate(user, sid):
    """End ONE of the user's own sessions (by its id). False when it is not
    theirs / not active."""
    token = _active_tokens(user).filter(jti=_current_jti_of(user, sid)).first()

    if token is None:
        return False

    BlacklistedToken.objects.get_or_create(token=token)
    return True


def terminate_others(user, current_sid):
    """End every session except the current one; returns how many."""
    count = 0

    for token in _active_tokens(user).exclude(jti=_current_jti_of(user, current_sid)):
        BlacklistedToken.objects.get_or_create(token=token)
        count += 1

    return count


# ---------------------------------------------------------------- rotation

# a refresh token used again within this many seconds of its rotation is two
# tabs (or a retry) refreshing at once - refused, never taken as theft
REUSE_GRACE_SECONDS = 60


def rotated(refresh):
    """After a refresh rotated the token: the session (its "sid") now runs on
    the new token's jti."""
    try:
        token = RefreshToken(refresh)
    except Exception:
        return
    sid = token.get("sid")
    if sid:
        UserLogin.objects.filter(token_jti=sid).update(current_jti=token["jti"])


def refresh_reused(refresh):
    """A refresh was refused. When the token is genuine but was ROTATED away
    (not the session's current one) and not just now, someone else holds a
    copy: end the session and its whole family, and audit it. Returns
    whether it did. Never fails."""
    from datetime import timedelta

    from rest_framework_simplejwt.state import token_backend

    try:
        payload = token_backend.decode(refresh, verify=True)   # signature + expiry, no blacklist
    except Exception:
        return False
    jti, sid = payload.get("jti"), payload.get("sid")
    login = UserLogin.objects.select_related("user").filter(token_jti=sid).first() if sid else None
    if login is None or _current(login) == jti:
        return False                                   # not a rotated token: a plain refusal
    black = BlacklistedToken.objects.filter(token__jti=jti).first()
    if black is None or black.blacklisted_at > timezone.now() - timedelta(seconds=REUSE_GRACE_SECONDS):
        return False

    ended = terminate_sso_family(login.user, sid)
    try:
        from django_resaas.saas.core.services import audit_service

        audit_service.record(action="SESSION_TOKEN_REUSED", target=login.user, actor=login.user,
                             details={"session": sid, "ended": ended})
    except Exception:
        pass
    return True


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

    jtis = [_current(member) for member in UserLogin.objects.filter(user=user, sso_family=login.sso_family)]
    count = 0

    for token in _active_tokens(user).filter(jti__in=list(jtis)):
        BlacklistedToken.objects.get_or_create(token=token)
        count += 1

    return count


def session_ended(sid):
    """Whether session `sid` has been ended (its current refresh token
    blacklisted). A rotation blacklists the PREVIOUS token, never this one."""
    if not sid:
        return False
    login = UserLogin.objects.filter(token_jti=sid).first()
    jti = _current(login) if login else sid
    return BlacklistedToken.objects.filter(token__jti=jti).exists()

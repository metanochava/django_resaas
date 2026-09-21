"""
Two-factor authentication (TOTP) and its policy by levels.

POLICY - one rule per level, resolved top to bottom:

    platform default  ->  EntityType  ->  Entity  ->  EntityUser

  * every level is INHERIT (no opinion), DISABLED, OPTIONAL or REQUIRED;
  * a REQUIRED anywhere above can NEVER be weakened by a level below it;
  * otherwise the most specific level that has an opinion wins.

A user can belong to several entities; at sign-in (before any entity is
chosen) two-factor is demanded when ANY of their entities resolves to REQUIRED.
An enrolled second factor is always enforced at sign-in, whatever the policy
says afterwards (DISABLED only means "this organisation does not offer it").

TOTP - RFC 6238 through pyotp. The secret is stored encrypted, a code is
accepted once (replay-proof), failures are rate-limited, recovery codes are
single-use keyed hashes. Nothing secret is ever logged.
"""
import hashlib
import hmac
import secrets
import time

import pyotp
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from django_resaas.saas.core.services import audit_service
from django_resaas.saas.core.utils.secret_box import decrypt_text, encrypt_text
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.two_factor import UserTwoFactor
from django_resaas.saas.models.two_factor_policy import TwoFactorPolicy

PURPOSE = "totp-secret"
STEP = 30
WINDOW = 1                      # accept the previous and next 30s step too

RECOVERY_CODES = 8
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

MAX_FAILURES = 5
LOCK_SECONDS = 300

CHALLENGE_SALT = "resaas.two_factor.challenge"
CHALLENGE_TTL = 300             # seconds to finish a two-factor sign-in

ENABLED = "TWO_FACTOR_ENABLED"
DISABLED_EVENT = "TWO_FACTOR_DISABLED"
RECOVERY_USED = "TWO_FACTOR_RECOVERY_USED"
RECOVERY_REGENERATED = "TWO_FACTOR_RECOVERY_REGENERATED"

NOT_CONFIGURED = "not_configured"
PENDING = "pending"
ACTIVE = "active"


class TwoFactorError(Exception):
    """`code` is stable and machine-readable; the view translates `message`."""

    def __init__(self, code, message, http_status=400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(code)


# ------------------------------------------------------------------ policy

def default_policy():
    value = getattr(settings, "TWO_FACTOR_DEFAULT_POLICY", TwoFactorPolicy.OPTIONAL)
    return value if value in TwoFactorPolicy.values and value != TwoFactorPolicy.INHERIT else TwoFactorPolicy.OPTIONAL


def resolve_policy(*levels):
    """Combine level policies (top -> bottom, INHERIT/None = no opinion)."""
    chosen = [level for level in levels if level and level != TwoFactorPolicy.INHERIT]

    if TwoFactorPolicy.REQUIRED in chosen:
        return TwoFactorPolicy.REQUIRED

    return chosen[-1] if chosen else default_policy()


def effective_policy(user, entity):
    """The policy for `user` inside `entity` (EntityType > Entity > EntityUser)."""
    membership = EntityUser.objects.filter(user=user, entity=entity).first()

    return resolve_policy(
        entity.entity_type.two_factor_policy if entity.entity_type_id else None,
        entity.two_factor_policy,
        membership.two_factor_policy if membership else None,
    )


def requires_two_factor(user):
    """Sign-in level: does ANY entity of this user require two-factor?"""
    memberships = EntityUser.objects.filter(user=user).select_related("entity", "entity__entity_type")

    return any(
        effective_policy(user, membership.entity) == TwoFactorPolicy.REQUIRED
        for membership in memberships
    )


# ------------------------------------------------------------------ state

def _row(user):
    return UserTwoFactor.objects.filter(user_id=user.pk).first()


def state_of(user):
    row = _row(user)

    if row is None:
        return NOT_CONFIGURED

    return ACTIVE if row.active else PENDING


def is_active(user):
    return state_of(user) == ACTIVE


def details(user, entity=None):
    row = _row(user)

    policy = effective_policy(user, entity) if entity is not None else (
        TwoFactorPolicy.REQUIRED if requires_two_factor(user) else default_policy()
    )

    return {
        "state": state_of(user),
        "policy": policy,
        "recovery_codes_remaining": len(row.recovery_hashes) if row and row.active else 0,
        "can_setup": policy != TwoFactorPolicy.DISABLED,
        "can_disable": policy != TwoFactorPolicy.REQUIRED,
    }


def summary_for(user, entity_id=None):
    """The read-only view an administrator gets of someone else's two-factor:
    the policy in force and whether the account has an ACTIVE factor. Never any
    secret, code or recovery-code detail."""
    from django_resaas.saas.models.entity import Entity

    entity = Entity.objects.filter(pk=entity_id).select_related("entity_type").first() if entity_id else None
    policy = effective_policy(user, entity) if entity is not None else (
        TwoFactorPolicy.REQUIRED if requires_two_factor(user) else default_policy()
    )

    return {"policy": policy, "state": ACTIVE if is_active(user) else NOT_CONFIGURED}


# ------------------------------------------------------------------ TOTP

def _totp(row):
    return pyotp.TOTP(decrypt_text(row.secret_encrypted, purpose=PURPOSE), interval=STEP)


def _fail_key(user):
    return f"two_factor:failures:{user.pk}"


def _check_not_locked(user):
    if cache.get(_fail_key(user), 0) >= MAX_FAILURES:
        raise TwoFactorError("too_many_attempts", "Too many attempts. Try again in a few minutes.", 429)


def _register_failure(user):
    key = _fail_key(user)
    cache.add(key, 0, LOCK_SECONDS)

    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOCK_SECONDS)


def _clear_failures(user):
    cache.delete(_fail_key(user))


def _matching_step(row, code, now=None):
    """The time step `code` belongs to (within the window), or None."""
    code = str(code or "").strip().replace(" ", "")

    if not (code.isdigit() and len(code) == 6):
        return None

    totp = _totp(row)
    current = int((now if now is not None else time.time()) // STEP)

    for step in range(current - WINDOW, current + WINDOW + 1):
        if hmac.compare_digest(totp.at(step * STEP), code):
            return step

    return None


def begin_setup(user):
    """(Re)issue a PENDING secret. Refused while a factor is already active."""
    if is_active(user):
        raise TwoFactorError("two_factor_already_active", "Two-factor authentication is already active.", 409)

    secret = pyotp.random_base32()

    UserTwoFactor.objects.update_or_create(
        user=user,
        defaults={"secret_encrypted": encrypt_text(secret, purpose=PURPOSE), "confirmed_at": None, "last_used_step": 0, "recovery_hashes": []},
    )

    issuer = getattr(settings, "TWO_FACTOR_ISSUER", "RESAAS")
    label = user.email or user.username

    return {
        "secret": secret,
        "otpauth_uri": pyotp.TOTP(secret, interval=STEP).provisioning_uri(name=label, issuer_name=issuer),
    }


def qr_data_uri(uri):
    """The provisioning URI as a PNG data URI (the project's own QR helper)."""
    from django_resaas.saas.core.utils.bar_qr_code_64 import make_qr_b64

    return f"data:image/png;base64,{make_qr_b64(uri)}"


def confirm_setup(user, code, request=None):
    """Prove the first code: the factor becomes ACTIVE; returns the recovery codes.

    Atomic and idempotent under retries / double clicks: the row is locked, so
    two concurrent confirmations cannot both activate it (the second sees it
    already active and is refused with 409)."""
    _check_not_locked(user)

    with transaction.atomic():
        row = UserTwoFactor.objects.select_for_update().filter(user_id=user.pk).first()

        if row is None or row.active:
            raise TwoFactorError("two_factor_not_pending", "There is no two-factor setup in progress.", 409)

        step = _matching_step(row, code)

        if step is None:
            _register_failure(user)
            raise TwoFactorError("invalid_code", "Invalid or expired code", 400)

        _clear_failures(user)

        row.confirmed_at = timezone.now()
        row.last_used_step = step
        codes = _new_recovery_codes(row)
        row.save()
        audit_service.record(action=ENABLED, target=user, actor=user, request=request)

    return codes


def verify(user, code, request=None):
    """Accept a TOTP code OR a recovery code for an ACTIVE factor (once each).

    Replay-proof under concurrency: the time step is claimed with a single
    conditional UPDATE (`last_used_step < step`), so of two simultaneous
    requests carrying the same code exactly one wins; recovery codes are
    consumed under a row lock for the same reason."""
    _check_not_locked(user)

    row = _row(user)

    if row is None or not row.active:
        raise TwoFactorError("two_factor_not_active", "Two-factor authentication is not active.", 409)

    step = _matching_step(row, code)

    if step is not None:
        claimed = UserTwoFactor.objects.filter(pk=row.pk, last_used_step__lt=step).update(last_used_step=step)

        if claimed:
            _clear_failures(user)
            return "totp"

    if _consume_recovery_code(row.pk, code):
        _clear_failures(user)
        audit_service.record(action=RECOVERY_USED, target=user, actor=user, request=request)
        return "recovery"

    _register_failure(user)
    raise TwoFactorError("invalid_code", "Invalid or expired code", 400)


def disable(user, code, request=None):
    """Turn the factor off - needs a valid code, and a REQUIRED policy forbids it."""
    if requires_two_factor(user):
        raise TwoFactorError("two_factor_required_by_policy", "Your organisation requires two-factor authentication.", 403)

    verify(user, code, request=request)

    with transaction.atomic():
        UserTwoFactor.objects.filter(user_id=user.pk).delete()
        audit_service.record(action=DISABLED_EVENT, target=user, actor=user, request=request)


def regenerate_recovery_codes(user, code, request=None):
    verify(user, code, request=request)

    row = _row(user)

    with transaction.atomic():
        codes = _new_recovery_codes(row)
        row.save(update_fields=["recovery_hashes"])
        audit_service.record(action=RECOVERY_REGENERATED, target=user, actor=user, request=request)

    return codes


# ------------------------------------------------------------------ recovery codes

def _hash_code(code):
    normalised = str(code or "").strip().upper().replace("-", "").replace(" ", "")

    return hmac.new(settings.SECRET_KEY.encode(), normalised.encode(), hashlib.sha256).hexdigest()


def _new_recovery_codes(row):
    """Replace the stored hashes; returns the plaintext codes ONCE."""
    codes = ["".join(secrets.choice(_ALPHABET) for _ in range(10)) for _ in range(RECOVERY_CODES)]
    row.recovery_hashes = [_hash_code(code) for code in codes]

    return [f"{code[:5]}-{code[5:]}" for code in codes]


def _consume_recovery_code(row_pk, code):
    """Burn one recovery code. Locked read-modify-write: two concurrent uses of
    the same code cannot both succeed."""
    candidate = _hash_code(code)

    with transaction.atomic():
        row = UserTwoFactor.objects.select_for_update().get(pk=row_pk)

        for stored in row.recovery_hashes:
            if hmac.compare_digest(stored, candidate):
                row.recovery_hashes = [item for item in row.recovery_hashes if item != stored]
                row.save(update_fields=["recovery_hashes"])
                return True

    return False


# ------------------------------------------------------------------ sign-in challenge

def make_challenge(user, purpose):
    """A short-lived signed proof that the PASSWORD step succeeded (no session yet)."""
    return signing.dumps({"uid": str(user.pk), "purpose": purpose}, salt=CHALLENGE_SALT)


def read_challenge(token, purpose):
    """The user a valid, unexpired challenge of `purpose` belongs to."""
    from django_resaas.saas.models.user import User

    try:
        payload = signing.loads(str(token or ""), salt=CHALLENGE_SALT, max_age=CHALLENGE_TTL)
    except signing.BadSignature:
        raise TwoFactorError("invalid_challenge", "This sign-in step has expired. Sign in again.", 401)

    user = User.objects.filter(pk=payload.get("uid"), is_active=True).first() if payload.get("purpose") == purpose else None

    if user is None:
        raise TwoFactorError("invalid_challenge", "This sign-in step has expired. Sign in again.", 401)

    return user


LOGIN = "login"
SETUP = "setup"


def sign_in_gate(user):
    """What must happen before this user gets a session: None (nothing), or
    ('two_factor_required', challenge) / ('two_factor_setup_required', challenge)."""
    if is_active(user):
        return "two_factor_required", make_challenge(user, LOGIN)

    if requires_two_factor(user):
        return "two_factor_setup_required", make_challenge(user, SETUP)

    return None


def sign_in_payload(user, request):
    """The sign-in answer once the PASSWORD step is done: either a session
    (tokens) or - when two-factor still has to happen - a challenge and NO tokens."""
    from django_resaas.saas.core.services import session_service

    payload = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "mobile": user.mobile,
        "must_change_password": False,
        "two_factor": "",
        "challenge": "",
        "tokens": None,
    }

    gate = sign_in_gate(user)

    if gate is not None:
        payload["two_factor"], payload["challenge"] = gate
        return payload

    payload["tokens"] = user.tokens()
    session_service.record_login(user, request, payload["tokens"])

    return payload

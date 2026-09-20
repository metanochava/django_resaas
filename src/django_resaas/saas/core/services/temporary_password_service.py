"""
Lifecycle of a TEMPORARY password.

    TEMPORARY  (row exists, encrypted copy present, not expired)
        - User.password holds the normal Django hash
        - UserTemporaryPassword.encrypted holds a Fernet copy an authorised
          administrator can reveal (audited)
        - the user must replace it before getting any session
    EXPIRED    (row exists, expired; the encrypted copy is already gone)
        - login is refused, nothing is revealed; an administrator can only
          issue a new one
    PERMANENT  (no row)
        - the user chose the password: no recoverable copy exists, ever

Every transition is atomic and audited. The plaintext is never logged, never
stored in clear, never returned by the normal User serializer.
"""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from django_resaas.saas.core.services import audit_service
from django_resaas.saas.core.tenant.current import current_entity_id
from django_resaas.saas.core.utils.secret_box import decrypt_text, encrypt_text
from django_resaas.saas.models.user_temporary_password import UserTemporaryPassword

logger = logging.getLogger(__name__)

PURPOSE = "temporary-password"

TEMPORARY = "temporary"
EXPIRED = "expired"
PERMANENT = "permanent"

CREATED = "TEMPORARY_PASSWORD_CREATED"
REGENERATED = "TEMPORARY_PASSWORD_REGENERATED"
VIEWED = "TEMPORARY_PASSWORD_VIEWED"
EXPIRED_EVENT = "TEMPORARY_PASSWORD_EXPIRED"
CHANGED = "TEMPORARY_PASSWORD_CHANGED"
PASSWORD_CHANGED = "PASSWORD_CHANGED"

_LETTERS_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # no I / O
_LETTERS_LOWER = "abcdefghijkmnopqrstuvwxyz"   # no l
_DIGITS = "23456789"                            # no 0 / 1
_SYMBOLS = "@#$%&*?!"
LENGTH = 12


class TemporaryPasswordError(Exception):
    """`code` is a stable machine code; the view translates the message."""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(code)


def ttl_hours():
    return int(getattr(settings, "TEMPORARY_PASSWORD_TTL_HOURS", 72))


def generate():
    """A random, easy-to-read-out-loud password with every character class."""
    required = [
        get_random_string(1, _LETTERS_UPPER),
        get_random_string(1, _LETTERS_LOWER),
        get_random_string(1, _DIGITS),
        get_random_string(1, _SYMBOLS),
    ]
    rest = get_random_string(LENGTH - len(required), _LETTERS_UPPER + _LETTERS_LOWER + _DIGITS)

    characters = required + list(rest)
    secrets.SystemRandom().shuffle(characters)

    return "".join(characters)


def _row(user):
    return UserTemporaryPassword.objects.filter(user_id=user.pk).first()


def state_of(user):
    """TEMPORARY / EXPIRED / PERMANENT - also retires an overdue copy."""
    row = _row(user)

    if row is None:
        return PERMANENT

    if row.expires_at <= timezone.now():
        _retire(row)
        return EXPIRED

    return TEMPORARY


def _retire(row):
    """Expiry: drop the recoverable copy for good (once) and audit it."""
    if row.encrypted is None:
        return

    with transaction.atomic():
        row.encrypted = None
        row.save(update_fields=["encrypted"])
        audit_service.record(action=EXPIRED_EVENT, target=row.user, entity_id=row.entity_id)


def expire_overdue():
    """Sweep: retire every overdue copy (management command / scheduler)."""
    overdue = UserTemporaryPassword.objects.filter(
        expires_at__lte=timezone.now(), encrypted__isnull=False
    ).select_related("user")

    count = 0
    for row in overdue:
        _retire(row)
        count += 1

    return count


def issue(user, *, actor=None, request=None, entity_id=None, regenerate=False):
    """
    (Re)issue a temporary password for `user`. The previous one - its hash and
    its recoverable copy - is replaced, so only ONE can ever be active.
    The plaintext is never returned: an administrator reads it back through
    reveal(), which is audited.
    """
    password = generate()
    entity_id = entity_id or getattr(request, "entity_id", None) or current_entity_id()

    with transaction.atomic():
        # set_password() normally retires the temporary copy (the user chose a
        # password); issuing one is the exception
        user._temporary_password_issuing = True
        try:
            user.set_password(password)
            user.save(update_fields=["password"])
        finally:
            user._temporary_password_issuing = False

        UserTemporaryPassword.objects.update_or_create(
            user=user,
            defaults={
                "encrypted": encrypt_text(password, purpose=PURPOSE),
                "expires_at": timezone.now() + timedelta(hours=ttl_hours()),
                "created_by": actor if getattr(actor, "pk", None) else None,
                "entity_id": entity_id,
            },
        )

        audit_service.record(
            action=REGENERATED if regenerate else CREATED,
            target=user, actor=actor, request=request, entity_id=entity_id,
        )


def reveal(user, *, actor, request=None):
    """The plaintext of a still-valid temporary password (audited)."""
    state = state_of(user)

    if state == PERMANENT:
        raise TemporaryPasswordError("no_temporary_password", "This user has no temporary password.")

    if state == EXPIRED:
        raise TemporaryPasswordError("temporary_password_expired", "The temporary password has expired. Generate a new one.")

    row = _row(user)

    with transaction.atomic():
        password = decrypt_text(row.encrypted, purpose=PURPOSE)
        audit_service.record(action=VIEWED, target=user, actor=actor, request=request)

    return password


def discard_on_password_change(user):
    """
    Called by User.save() right after ANY new password was stored (own change,
    reset by e-mail/OTP, first-login change...): a definitive password is never
    recoverable, so the temporary copy is HARD-deleted in that same save and the
    change audited. Not called while a temporary password is being issued.
    """
    if getattr(user, "_temporary_password_issuing", False):
        return

    removed, _ = UserTemporaryPassword.objects.filter(user_id=user.pk).delete()

    # the reverse one-to-one may be cached on this instance
    user._state.fields_cache.pop("temporary_password", None)

    if removed:
        audit_service.record(action=CHANGED, target=user, actor=user)
    elif not getattr(user, "_password_change_is_creation", False):
        # an ordinary change of a password the user already had
        audit_service.record(action=PASSWORD_CHANGED, target=user, actor=user)


def complete(user, new_password):
    """The user chose a definitive password (atomic: hash + copy removal)."""
    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])


def details(user):
    """Non-secret state for the User details screen."""
    state = state_of(user)
    row = _row(user)

    return {
        "state": state,
        "must_change_password": state in (TEMPORARY, EXPIRED),
        "expires_at": row.expires_at if row else None,
        "can_reveal": state == TEMPORARY,
    }

"""
CREATE Person -> create its User (and only then).

The User is created exclusively when a Person is created (post_save with
created=True, see core/signals/permissions.py); an UPDATE never creates a
User, never regenerates a username and never touches an existing one - not
even for an old Person that has no User yet.

The username is built from the Person's FIRST NAME ONLY (never the surname,
middle name or full name):

    João Manuel Silva -> joao          (first one)
    João Cossa        -> joao.a83f21   (name taken: random suffix, never the surname)

User.username is UNIQUE in the database; generate_unique_username() only
picks a likely-free candidate, the UNIQUE constraint is what actually
guarantees uniqueness across concurrent workers, and create_user_for_person()
retries with a fresh suffix when - and only when - the failure was a
username collision.
"""
import re
import secrets
import unicodedata

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

User = get_user_model()

# Every retry after the first one uses a random suffix, so a handful of
# attempts is already far more than a real collision streak.
MAX_USERNAME_ATTEMPTS = 8

SUFFIX_BYTES = 3            # token_hex(3) -> 6 hex characters
NEUTRAL_BASE = "user"


def username_max_length():
    return User._meta.get_field("username").max_length


def first_name_of(name):
    """First word of Person.name ('João Manuel' -> 'João'), '' when none."""
    words = str(name or "").split()

    return words[0] if words else ""


def normalize_username_base(name):
    """Lowercase, accents removed, only a-z0-9 kept; '' when nothing usable."""
    text = unicodedata.normalize("NFKD", first_name_of(name))
    text = text.encode("ascii", "ignore").decode("ascii").lower()

    return re.sub(r"[^a-z0-9]", "", text)


def _with_suffix(base):
    suffix = secrets.token_hex(SUFFIX_BYTES)
    room = username_max_length() - len(suffix) - 1

    return f"{base[:max(room, 1)]}.{suffix}"


def generate_unique_username(name, *, force_suffix=False):
    """
    A username for `name` that is free right now: the plain first name when
    available, otherwise '<first name>.<random suffix>' (or 'user.<suffix>'
    when the name has no usable first name). Never empty, never longer than
    the field allows. This is only a best guess - the database UNIQUE
    constraint is the real guarantee (see create_user_for_person()).
    """
    base = normalize_username_base(name)[:username_max_length()]

    if base and not force_suffix and not User.objects.filter(username__iexact=base).exists():
        return base

    for _ in range(MAX_USERNAME_ATTEMPTS):
        candidate = _with_suffix(base or NEUTRAL_BASE)

        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate

    return _with_suffix(base or NEUTRAL_BASE)


def create_user_for_person(person):
    """
    Creates and links the User of a NEW Person. Only a username collision is
    retried; any other IntegrityError (e.g. the e-mail already belongs to
    another User) is a real problem and is raised untouched.
    """
    user = None
    force_suffix = False

    for _ in range(MAX_USERNAME_ATTEMPTS):
        username = generate_unique_username(person.name, force_suffix=force_suffix)

        user = User(
            username=username,
            email=person.email or None,
            first_name=person.name or "",
            last_name=person.surname or "",
            state=person.state or "Active",
        )
        user.set_unusable_password()  # replaced by the temporary password right after linking

        # The Person already exists: the User -> Person signal must not
        # create a second one, and the two-way field sync has nothing to do.
        user._skip_person_autocreate = True
        user._skip_sync = True

        try:
            with transaction.atomic():
                user.save()
            break
        except IntegrityError:
            if not User.objects.filter(username=username).exists():
                raise  # not a username collision - do not hide it

            force_suffix = True
    else:
        raise IntegrityError("Could not generate a unique username.")

    # update() (not save()): linking must not re-trigger the sync signals
    type(person).objects.filter(pk=person.pk).update(user=user)
    person.user = user

    # The new account starts with a TEMPORARY password (hash + audited,
    # encrypted copy an authorised administrator can read back until the
    # user replaces it) - see temporary_password_service.py.
    from django_resaas.saas.core.services import temporary_password_service

    temporary_password_service.issue(user, actor=getattr(person, "created_by", None))

    return user

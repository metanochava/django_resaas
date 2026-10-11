"""Username rules - one place for the registration form, the availability
check (register/username/) and account creation.

A username is a public, readable handle, not the login identity (User.
USERNAME_FIELD is the email; login also accepts mobile and username):

    ^[a-z][a-z0-9._]{2,29}$   3-30 chars, lowercase, starts with a letter,
                              no ".." / "__" / "._" runs, no trailing "." or "_"

Starting with a letter means a username can never equal a phone number, and
"@" is not allowed, so it can never equal an email - login looks the three up
together. Uniqueness is case-insensitive; new usernames are stored lowercase,
so the database UNIQUE constraint is the final guarantee between concurrent
registrations.
"""
import re

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30

_PATTERN = re.compile(r"^[a-z][a-z0-9._]{%d,%d}$" % (USERNAME_MIN_LENGTH - 1, USERNAME_MAX_LENGTH - 1))
_SEPARATOR_RUN = re.compile(r"[._]{2,}")


def normalize_username(value):
    """What the user typed -> the stored form (trimmed, lowercase)."""
    return str(value or "").strip().lower()


def username_is_valid(value):
    """True when the (already normalized) value follows the rules above."""
    return bool(
        _PATTERN.match(value or "")
        and not _SEPARATOR_RUN.search(value)
        and value[-1] not in "._"
    )


def username_is_taken(value):
    from django.apps import apps

    User = apps.get_model("django_resaas", "User")
    return User.objects.filter(username__iexact=value).exists()


class UserName:
    """
    DEPRECATED - no longer used by registration (it silently changed a taken
    username into another one the user never chose). Kept for code outside
    the framework that may still import it; use the functions above.
    """

    @staticmethod
    def Create(name):
        from django.apps import apps  # lazy import

        User = apps.get_model('django_resaas', 'User')

        try:
            user = User.objects.get(username=name)
        except User.DoesNotExist:
            return name

        username = user.username

        # separar letras e números
        letras = "".join(filter(str.isalpha, username))
        numeros = "".join(filter(str.isdigit, username))

        numero = int(numeros) if numeros else 0
        novo_username = f"{letras}{numero + 1}"

        return UserName.Create(novo_username)

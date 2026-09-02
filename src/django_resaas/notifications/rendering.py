import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template import Context, Template

# Same E.164 shape already enforced on write by the quasar_resaas frontend
# (utils/phone.js) - kept in sync deliberately, not re-derived.
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def is_valid_email(value):
    if not value:
        return False
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False


def is_valid_e164(value):
    return bool(value) and bool(_E164_RE.match(value))


def resolve_language_code(recipient_language_code, notification_settings):
    """recipient language -> entity default (NotificationSettings) ->
    Django's LANGUAGE_CODE. Never guesses a country/locale beyond that."""

    if recipient_language_code:
        return recipient_language_code

    if notification_settings and notification_settings.default_language_id:
        return notification_settings.default_language.code

    return getattr(settings, "LANGUAGE_CODE", "en-us")


def render_template(template, context):
    """Render a NotificationTemplate's subject/body with the Django
    Template Engine (the same engine already used by the project) - never
    Python eval/exec, `context` is a plain dict."""

    ctx = Context(context)

    body = Template(template.body).render(ctx)
    subject = Template(template.subject).render(ctx) if template.subject else None

    return subject, body


def pick_template(rule, language_code):
    """rule.templates filtered by language code, falling back to the
    rule's default (language=null) template. Returns None if neither
    exists - the engine treats that as a permanent failure (missing
    template, spec section 42)."""

    templates = {
        t.language.code if t.language_id else None: t
        for t in rule.templates.filter(enabled=True)
    }

    return templates.get(language_code) or templates.get(None)

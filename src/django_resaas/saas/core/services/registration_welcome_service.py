"""Welcome notification sent right after a self-registration completes
(data/user/views/register.py's RegisterAPIView) - confirms account
creation over whichever channel the person actually verified during
registration (email or mobile).

Distinct from bootstrap_email_service.py: that one is for the
interactive create_root/create_entity commands, which always have a
real Entity/EntityType/Branch/tenant context. A self-registered end
user has none of that yet, just a username and one verified
email/mobile - so this reuses the same BOOTSTRAP_WELCOME email
template (its Entity/Branch/instructions/login/password blocks are
all optional and simply don't render when omitted) rather than adding
a second template for what is otherwise the same "your account is
ready" message.

Never raises: registration has already succeeded by the time this
runs - a missing/misconfigured notification provider must not turn a
successful signup into an error response."""
import logging

from django_resaas.saas.core.utils.email_branding import resolve_email_branding
from django_resaas.saas.core.utils.templates import render_email_template
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers import NotificationProviderRegistry

logger = logging.getLogger(__name__)


def send_registration_welcome(user, channel, request=None):
    """`channel` is the same "email"/"mobile" value RegisterSerializer
    validated - the channel the person just proved they control, and
    therefore the only one guaranteed to reach them."""
    try:
        if channel == "email":
            return _send_welcome_email(user, request)
        if channel == "mobile":
            return _send_welcome_sms(user, request)
        return False
    except Exception as exc:
        logger.warning("[register] welcome notification not sent to user %s: %s", user.pk, exc)
        return False


def _send_welcome_email(user, request):
    provider = NotificationProviderRegistry.get(Channel.EMAIL)
    if provider is None or not user.email:
        return False

    entity_name, logo_url = resolve_email_branding(request)

    html = render_email_template("BOOTSTRAP_WELCOME", {
        "entity_name": entity_name,
        "logo": logo_url,
        "greeting": Translate.tdc(request, "Welcome, {username}!").format(username=user.username),
        "intro": Translate.tdc(request, "Your account has been created successfully."),
        "username_label": Translate.tdc(request, "Username"),
        "username": user.username,
        "email_label": Translate.tdc(request, "Email"),
        "email": user.email,
        "security_notice": Translate.tdc(
            request, "This is an automated message confirming your account was created.",
        ),
        "footer_notice": Translate.tdc(request, "This is an automated message, please do not reply."),
    })

    plain_body = Translate.tdc(
        request, "Welcome, {username}! Your account ({email}) was created successfully.",
    ).format(username=user.username, email=user.email)

    provider.send(
        recipient=user.email,
        subject=Translate.tdc(request, "Welcome to RESAAS"),
        body=plain_body,
        metadata={"html": html},
    )
    return True


def _send_welcome_sms(user, request):
    provider = NotificationProviderRegistry.get(Channel.SMS)
    if provider is None or not user.mobile:
        return False

    body = Translate.tdc(
        request, "Welcome, {username}! Your RESAAS account has been created successfully.",
    ).format(username=user.username)

    provider.send(recipient=user.mobile, body=body)
    return True

"""
OTP delivery/verification for proving someone controls an email address
or phone number before it's trusted - registration (no User row exists
yet), and changing an already-authenticated user's email/mobile (see
data/user/views/profile_contact_otp.py - required so email/mobile can
never change via a generic PATCH without re-proving ownership first).
Deliberately time-based (pyotp.TOTP, 5 minute window) rather than the
counter-based pyotp.HOTP the existing mobile-password-reset flow uses
(see data/user/views/change_password_mobile.py) - HOTP needs somewhere
to persist a counter, and at registration time there is no User row yet
to hold one; using the same time-based scheme for the profile-change
case too keeps one mechanism instead of two. Reuses the same
key-derivation utility (generateKeyOTP) either way.

Sent synchronously/directly via the notification providers' `.send()` -
NOT through NotificationOutbox/EventDispatcher. A user waiting on-screen
for a code needs it in seconds; the async, retry-with-backoff Outbox
pipeline is for business events, not this.
"""

import base64

import pyotp

from django_resaas.engine.core.utils.email_branding import resolve_email_branding
from django_resaas.engine.core.utils.generate_key_otp import generateKeyOTP
from django_resaas.engine.core.utils.templates import render_email_template
from django_resaas.engine.core.utils.translate import Translate
from django_resaas.notifications.enums import Channel
from django_resaas.notifications.exceptions import NotificationError
from django_resaas.notifications.providers import NotificationProviderRegistry

OTP_INTERVAL_SECONDS = 300

# Registration channel -> notification provider channel. "mobile" is the
# public/API name (matches the User.mobile field); the providers registry
# uses "sms" as its channel key.
_PROVIDER_CHANNEL = {
    "email": Channel.EMAIL,
    "mobile": Channel.SMS,
}


def _totp_for(identifier):
    key = base64.b32encode(generateKeyOTP().returnValue(identifier).encode())
    return pyotp.TOTP(key, interval=OTP_INTERVAL_SECONDS)


_INTRO_BY_PURPOSE = {
    "register": "Use the code below to confirm your registration.",
    "email_change": "Use the code below to confirm your new email address.",
    "mobile_change": "Use the code below to confirm your new phone number.",
}


def send_registration_otp(channel, identifier, request=None, purpose="register"):
    """Generates and delivers a fresh OTP for `identifier` over `channel`
    ("email" or "mobile"). Raises whatever NotificationError subclass the
    provider raises (ProviderConfigurationError/ProviderTemporaryError/
    ProviderPermanentError) on delivery failure - callers decide how to
    translate/respond.

    `request`, when given, is used only for best-effort Entity branding
    (logo + name) on the HTML email - see email_branding.py. Never
    required: with no request (or no Entity resolved from it) the email
    still sends, just without a logo.

    `purpose` only changes the wording of the email/SMS body - the OTP
    itself is identical regardless (same TOTP over the same identifier)."""

    totp = _totp_for(identifier)
    code = totp.now()

    provider_channel = _PROVIDER_CHANNEL[channel]
    provider = NotificationProviderRegistry.get(provider_channel)

    if provider is None:
        raise NotificationError(
            f"No provider registered for channel={provider_channel!r}."
        )

    plain_body = Translate.tdc(
        request, "Your verification code is {code}. It expires in 5 minutes."
    ).format(code=code)

    if channel == "email":
        entity_name, logo_url = resolve_email_branding(request)

        html = render_email_template(
            "OTP_CODE",
            {
                "entity_name": entity_name,
                "logo": logo_url,
                "code": code,
                "greeting": Translate.tdc(request, "Hello,"),
                "intro": Translate.tdc(
                    request, _INTRO_BY_PURPOSE.get(purpose, _INTRO_BY_PURPOSE["register"])
                ),
                "expiry_notice": Translate.tdc(
                    request,
                    "This code expires in 5 minutes. If you didn't request it, "
                    "you can safely ignore this email.",
                ),
                "footer_notice": Translate.tdc(
                    request, "This is an automated message, please do not reply."
                ),
            },
        )

        provider.send(
            recipient=identifier,
            subject=Translate.tdc(request, "Your verification code"),
            body=plain_body,
            metadata={"html": html},
        )
    else:
        provider.send(recipient=identifier, body=plain_body)


def verify_registration_otp(channel, identifier, code):
    """Returns True iff `code` is a currently-valid OTP for `identifier`.
    Never raises on a wrong/expired code - that's just `False`."""

    if not code:
        return False

    totp = _totp_for(identifier)
    return bool(totp.verify(str(code)))

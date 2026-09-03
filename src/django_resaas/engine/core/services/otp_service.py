"""
OTP delivery/verification for flows that happen BEFORE a User row exists
(registration by email or mobile). Deliberately time-based (pyotp.TOTP,
5 minute window) rather than the counter-based pyotp.HOTP the existing
mobile-password-reset flow uses (see
data/user/views/change_password_mobile.py) - HOTP needs somewhere to
persist a counter, and at registration time there is no User row yet to
hold one. Reuses the same key-derivation utility (generateKeyOTP) either
way, just swaps HOTP for TOTP for this specific pre-account case.

Sent synchronously/directly via the notification providers' `.send()` -
NOT through NotificationOutbox/EventDispatcher. A user waiting on-screen
for a registration code needs it in seconds; the async, retry-with-backoff
Outbox pipeline is for business events, not this.
"""

import base64

import pyotp

from django_resaas.engine.core.utils.generate_key_otp import generateKeyOTP
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


def send_registration_otp(channel, identifier):
    """Generates and delivers a fresh OTP for `identifier` over `channel`
    ("email" or "mobile"). Raises whatever NotificationError subclass the
    provider raises (ProviderConfigurationError/ProviderTemporaryError/
    ProviderPermanentError) on delivery failure - callers decide how to
    translate/respond."""

    totp = _totp_for(identifier)
    code = totp.now()

    provider_channel = _PROVIDER_CHANNEL[channel]
    provider = NotificationProviderRegistry.get(provider_channel)

    if provider is None:
        raise NotificationError(
            f"No provider registered for channel={provider_channel!r}."
        )

    if channel == "email":
        provider.send(
            recipient=identifier,
            subject="Your verification code",
            body=f"Your verification code is {code}. It expires in 5 minutes.",
        )
    else:
        provider.send(
            recipient=identifier,
            body=f"Your verification code is {code}. It expires in 5 minutes.",
        )


def verify_registration_otp(channel, identifier, code):
    """Returns True iff `code` is a currently-valid OTP for `identifier`.
    Never raises on a wrong/expired code - that's just `False`."""

    if not code:
        return False

    totp = _totp_for(identifier)
    return bool(totp.verify(str(code)))

"""Rate limits of the PUBLIC registration endpoints (same mechanism as the
public site's SiteContactThrottle: DRF SimpleRateThrottle on Django's cache).
Each rate is a setting, so a deployment can tune it without code:

    RESAAS_REGISTER_OTP_THROTTLE_RATE          per client address   10/hour
    RESAAS_REGISTER_OTP_IDENTIFIER_THROTTLE_RATE per email / phone   5/hour
    RESAAS_REGISTER_THROTTLE_RATE              per client address   20/hour
    RESAAS_USERNAME_CHECK_THROTTLE_RATE        per client address   120/hour

The cache must be shared between workers (e.g. Redis) for the limits to hold
across processes; the default local-memory cache counts per process.
"""
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class _ByAddress(SimpleRateThrottle):
    setting = None
    default = None

    def get_rate(self):
        return getattr(settings, self.setting, self.default)

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class RegisterOTPThrottle(_ByAddress):
    scope = "register_otp"
    setting = "RESAAS_REGISTER_OTP_THROTTLE_RATE"
    default = "10/hour"


class RegisterOTPIdentifierThrottle(_ByAddress):
    """Per destination: one address cannot have codes sent to it repeatedly
    (SMS/e-mail flooding), whoever asks."""

    scope = "register_otp_identifier"
    setting = "RESAAS_REGISTER_OTP_IDENTIFIER_THROTTLE_RATE"
    default = "5/hour"

    def get_cache_key(self, request, view):
        identifier = str(request.data.get("identifier") or "").strip().lower()
        if not identifier:
            return None
        return self.cache_format % {"scope": self.scope, "ident": identifier}


class RegisterThrottle(_ByAddress):
    scope = "register"
    setting = "RESAAS_REGISTER_THROTTLE_RATE"
    default = "20/hour"


class UsernameCheckThrottle(_ByAddress):
    scope = "username_check"
    setting = "RESAAS_USERNAME_CHECK_THROTTLE_RATE"
    default = "120/hour"

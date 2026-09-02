import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from django_resaas.notifications.exceptions import (
    ProviderConfigurationError,
    ProviderPermanentError,
    ProviderTemporaryError,
)
from .base import BaseNotificationProvider

_TEMPORARY_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class SMSProvider(BaseNotificationProvider):
    """Twilio SMS, implemented with the stdlib (urllib) instead of the
    twilio SDK - keeps this an optional-in-spirit integration with zero
    new required dependency. Credentials come from env vars only, never
    stored in the database (spec section 19)."""

    name = "twilio"

    API_BASE = "https://api.twilio.com/2010-04-01"

    def _credentials(self):
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            raise ProviderConfigurationError(
                "SMSProvider: TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/"
                "TWILIO_FROM_NUMBER are not fully configured."
            )

        return account_sid, auth_token, from_number

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        account_sid, auth_token, from_number = self._credentials()

        url = f"{self.API_BASE}/Accounts/{account_sid}/Messages.json"

        data = urllib.parse.urlencode(
            {"To": recipient, "From": from_number, "Body": body or ""}
        ).encode()

        request = urllib.request.Request(url, data=data, method="POST")

        auth = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        request.add_header("Authorization", f"Basic {auth}")
        # Twilio doesn't accept a client idempotency key on this endpoint;
        # documented limitation (spec section 45).

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode())
                return {
                    "success": True,
                    "provider_message_id": payload.get("sid"),
                    "provider_status": payload.get("status"),
                    "raw": {"status": payload.get("status")},
                }
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            if exc.code in _TEMPORARY_HTTP_STATUS:
                raise ProviderTemporaryError(
                    f"Twilio HTTP {exc.code}: {body_text}"
                ) from exc
            raise ProviderPermanentError(
                f"Twilio HTTP {exc.code}: {body_text}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderTemporaryError(str(exc)) from exc

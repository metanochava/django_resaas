import json
import os
import urllib.error
import urllib.request

from django_resaas.notifications.exceptions import (
    ProviderConfigurationError,
    ProviderPermanentError,
    ProviderTemporaryError,
)
from .base import BaseNotificationProvider

_TEMPORARY_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class WhatsAppProvider(BaseNotificationProvider):
    """Meta WhatsApp Cloud API, implemented with the stdlib (urllib) - a
    plain REST call, no SDK dependency. `metadata` may carry
    provider_template_name/provider_template_id/provider_language for
    channels that require pre-approved templates; when absent this sends
    a plain text message (only valid within Meta's 24h session window)."""

    name = "meta_cloud_api"

    def _credentials(self):
        token = os.environ.get("WHATSAPP_CLOUD_API_TOKEN")
        phone_number_id = os.environ.get("WHATSAPP_CLOUD_API_PHONE_NUMBER_ID")
        api_version = os.environ.get("WHATSAPP_CLOUD_API_VERSION", "v20.0")

        if not token or not phone_number_id:
            raise ProviderConfigurationError(
                "WhatsAppProvider: WHATSAPP_CLOUD_API_TOKEN/"
                "WHATSAPP_CLOUD_API_PHONE_NUMBER_ID are not fully configured."
            )

        return token, phone_number_id, api_version

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        token, phone_number_id, api_version = self._credentials()
        metadata = metadata or {}

        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

        template_name = metadata.get("provider_template_name")

        if template_name:
            message_payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": metadata.get("provider_language", "en")},
                },
            }
        else:
            message_payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": body or ""},
            }

        request = urllib.request.Request(
            url,
            data=json.dumps(message_payload).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode())
                message_id = (payload.get("messages") or [{}])[0].get("id")
                return {
                    "success": True,
                    "provider_message_id": message_id,
                    "provider_status": "accepted",
                    "raw": {"contacts": payload.get("contacts")},
                }
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            if exc.code in _TEMPORARY_HTTP_STATUS:
                raise ProviderTemporaryError(
                    f"WhatsApp Cloud API HTTP {exc.code}: {body_text}"
                ) from exc
            raise ProviderPermanentError(
                f"WhatsApp Cloud API HTTP {exc.code}: {body_text}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderTemporaryError(str(exc)) from exc

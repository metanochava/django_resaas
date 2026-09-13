import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt

from django_resaas.notifications.exceptions import (
    ProviderConfigurationError,
    ProviderPermanentError,
    ProviderTemporaryError,
)
from .base import BaseNotificationProvider

_TEMPORARY_HTTP_STATUS = {408, 429, 500, 502, 503, 504}
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_TOKEN_EXPIRY_LEEWAY_SECONDS = 30


class FirebasePushProvider(BaseNotificationProvider):
    """Firebase Cloud Messaging (HTTP v1 API), implemented with the
    stdlib (urllib) plus PyJWT - already a transitive dependency of
    djangorestframework_simplejwt, made direct here - for the one part
    that genuinely needs a crypto primitive: signing the service
    account's JWT to obtain an OAuth2 access token. No firebase-admin/
    google-auth SDK, same zero-extra-SDK approach as SMSProvider/
    WhatsAppProvider.

    Credentials come from the FIREBASE_SERVICE_ACCOUNT_JSON env var
    (the whole service-account JSON as one string) only - never stored
    in the database. `recipient` is the target FCM device/registration
    token, not a phone number or email address."""

    name = "firebase"

    def __init__(self):
        self._access_token = None
        self._access_token_expiry = 0

    def _service_account(self):
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

        if not raw:
            raise ProviderConfigurationError(
                "FirebasePushProvider: FIREBASE_SERVICE_ACCOUNT_JSON is not configured."
            )

        try:
            account = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderConfigurationError(
                f"FirebasePushProvider: FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}"
            ) from exc

        if not account.get("client_email") or not account.get("private_key") or not account.get("project_id"):
            raise ProviderConfigurationError(
                "FirebasePushProvider: service account JSON is missing "
                "client_email/private_key/project_id."
            )

        return account

    def _access_token_for(self, account):
        now = int(time.time())

        if self._access_token and now < self._access_token_expiry - _TOKEN_EXPIRY_LEEWAY_SECONDS:
            return self._access_token

        claims = {
            "iss": account["client_email"],
            "scope": _SCOPE,
            "aud": _TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }
        assertion = jwt.encode(claims, account["private_key"], algorithm="RS256")

        data = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }).encode()

        request = urllib.request.Request(_TOKEN_URL, data=data, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            raise ProviderConfigurationError(
                f"FirebasePushProvider: token exchange rejected: {body_text}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderTemporaryError(str(exc)) from exc

        self._access_token = payload["access_token"]
        self._access_token_expiry = now + int(payload.get("expires_in", 3600))
        return self._access_token

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        account = self._service_account()
        token = self._access_token_for(account)
        metadata = metadata or {}

        notification = {}
        if subject:
            notification["title"] = subject
        if body:
            notification["body"] = body

        message = {"token": recipient}
        if notification:
            message["notification"] = notification
        if metadata.get("data"):
            message["data"] = {str(k): str(v) for k, v in metadata["data"].items()}

        url = f"https://fcm.googleapis.com/v1/projects/{account['project_id']}/messages:send"

        request = urllib.request.Request(
            url,
            data=json.dumps({"message": message}).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode())
                return {
                    "success": True,
                    "provider_message_id": payload.get("name"),
                    "provider_status": "sent",
                    "raw": {},
                }
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            if exc.code in _TEMPORARY_HTTP_STATUS:
                raise ProviderTemporaryError(
                    f"FCM HTTP {exc.code}: {body_text}"
                ) from exc
            raise ProviderPermanentError(
                f"FCM HTTP {exc.code}: {body_text}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderTemporaryError(str(exc)) from exc

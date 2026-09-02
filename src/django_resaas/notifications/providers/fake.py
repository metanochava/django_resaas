"""Fake providers for tests. The test suite must never contact a real
Email/SMS/WhatsApp service - every test that needs a provider should
register one of these (or a Mock wrapping the same interface) instead."""

import uuid

from .base import BaseNotificationProvider


class FakeProvider(BaseNotificationProvider):
    """Records every call in `.sent` and returns a configurable, fake
    success/failure so tests can assert on both without any network
    call. Configure failure via `.fail_with = SomeException("...")`."""

    name = "fake"

    def __init__(self):
        self.sent = []
        self.fail_with = None

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        self.sent.append(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "metadata": metadata,
                "idempotency_key": idempotency_key,
            }
        )

        if self.fail_with:
            raise self.fail_with

        return {
            "success": True,
            "provider_message_id": f"fake-{uuid.uuid4()}",
            "provider_status": "sent",
            "raw": {},
        }


class FakeEmailProvider(FakeProvider):
    name = "fake_email"


class FakeSMSProvider(FakeProvider):
    name = "fake_sms"


class FakeWhatsAppProvider(FakeProvider):
    name = "fake_whatsapp"

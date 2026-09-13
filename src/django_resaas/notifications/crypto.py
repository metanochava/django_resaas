"""Symmetric encryption for per-tenant provider credentials
(NotificationProviderCredential.encrypted_config) - the one place in
this app allowed to hold provider secrets at rest. Every provider
(SMSProvider/WhatsAppProvider/FirebasePushProvider) otherwise reads
credentials from env vars only, never the database (spec section 19) -
this module is what lets a tenant override that default safely,
without turning "safely" into "in plaintext".

Uses Fernet from `cryptography` (already a direct dependency, added
for FirebasePushProvider's JWT signing) instead of pulling in a
third-party encrypted-field package.
"""
import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    key = os.environ.get("NOTIFICATIONS_ENCRYPTION_KEY")

    if not key:
        # Zero-config fallback so this works out of the box - real
        # deployments that actually store tenant credentials should set
        # NOTIFICATIONS_ENCRYPTION_KEY explicitly (a Fernet.generate_key()
        # value) so rotating SECRET_KEY doesn't also silently break
        # decryption of every stored credential.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)

    return Fernet(key)


def encrypt_config(config: dict) -> str:
    return _fernet().encrypt(json.dumps(config).encode()).decode()


def decrypt_config(ciphertext: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(ciphertext.encode()).decode())
    except InvalidToken as exc:
        raise ValueError(
            "NotificationProviderCredential: could not decrypt stored config "
            "(wrong or rotated NOTIFICATIONS_ENCRYPTION_KEY/SECRET_KEY?)."
        ) from exc

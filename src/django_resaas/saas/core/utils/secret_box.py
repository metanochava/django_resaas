"""Reversible encryption for the few secrets RESAAS must be able to show again
(today: a TEMPORARY password until its owner replaces it).

Nothing home-made: Fernet (AES-128-CBC + HMAC-SHA256, authenticated) from the
`cryptography` package - the same primitive notifications/crypto.py already
uses for tenant provider credentials. The key comes from
RESAAS_ENCRYPTION_KEY (a Fernet.generate_key() value) when set; otherwise it is
derived from SECRET_KEY together with a purpose label, so the key protecting one
kind of secret never equals the one protecting another. Set the env var
explicitly in production so rotating SECRET_KEY does not orphan stored secrets.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class SecretBoxError(ValueError):
    """The stored ciphertext cannot be decrypted (wrong/rotated key, tampering)."""


def _fernet(purpose):
    key = os.environ.get("RESAAS_ENCRYPTION_KEY")

    if not key:
        material = f"{settings.SECRET_KEY}:{purpose}".encode()
        key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())

    return Fernet(key)


def encrypt_text(plaintext, *, purpose):
    return _fernet(purpose).encrypt(str(plaintext).encode()).decode()


def decrypt_text(ciphertext, *, purpose):
    try:
        return _fernet(purpose).decrypt(str(ciphertext).encode()).decode()
    except InvalidToken as exc:
        raise SecretBoxError("Could not decrypt the stored secret.") from exc

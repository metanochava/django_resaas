"""Retry backoff + error classification, shared by outbox_dispatcher.py
and tasks.py so the two never disagree on timing."""

import random

from django.conf import settings

from django_resaas.notifications.exceptions import (
    ProviderConfigurationError,
    ProviderPermanentError,
    ProviderTemporaryError,
)


def base_seconds():
    return getattr(settings, "OUTBOX_RETRY_BASE_SECONDS", 30)


def max_seconds():
    return getattr(settings, "OUTBOX_RETRY_MAX_SECONDS", 3600)


def max_attempts():
    return getattr(settings, "OUTBOX_MAX_ATTEMPTS", 5)


def compute_backoff_seconds(attempts):
    """Exponential backoff with jitter, capped at OUTBOX_RETRY_MAX_SECONDS.
    `attempts` is the number of attempts already made (1 after the first
    failure)."""

    delay = base_seconds() * (2 ** max(attempts - 1, 0))
    delay = min(delay, max_seconds())
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


def classify_exception(exc):
    """Map a provider exception to ("retry"|"failed", error_type,
    message). Anything not explicitly a notifications provider exception
    is treated as temporary - safer to retry an unexpected error than to
    silently drop the notification."""

    if isinstance(exc, ProviderConfigurationError):
        return "failed", "configuration", str(exc)

    if isinstance(exc, ProviderPermanentError):
        return "failed", "permanent", str(exc)

    if isinstance(exc, ProviderTemporaryError):
        return "retry", "temporary", str(exc)

    return "retry", "temporary", str(exc)

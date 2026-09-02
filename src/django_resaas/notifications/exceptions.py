class NotificationError(Exception):
    """Base class for every notifications-app exception."""


class ProviderConfigurationError(NotificationError):
    """A provider is selected but its required settings/credentials are
    missing or incomplete. Always a permanent failure - retrying will
    never fix a configuration error."""


class ProviderTemporaryError(NotificationError):
    """The provider (or the network) failed in a way that is expected to
    be transient - timeout, connection error, 429/500/502/503/504. The
    outbox row should move to `retry`."""


class ProviderPermanentError(NotificationError):
    """The provider rejected the message in a way retrying cannot fix -
    invalid recipient, rejected content, unknown template, etc. The
    outbox row should move to `failed` with no further retries."""


class InvalidTransitionError(NotificationError):
    """Raised by assert_transition() when a status change is not allowed
    by notifications/enums.py's VALID_TRANSITIONS."""

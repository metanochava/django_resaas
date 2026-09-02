class BaseNotificationProvider:
    """Common provider interface. NotificationEngine/worker never import a
    concrete provider directly - only through NotificationProviderRegistry."""

    #: Set by concrete providers, used for logging/DeliveryAttempt.provider.
    name = None

    def send(
        self, recipient, subject=None, body=None, metadata=None, idempotency_key=None
    ):
        """Send one message.

        Returns a normalized dict:
            {"success": bool, "provider_message_id": str|None,
             "provider_status": str|None, "raw": <sanitized>}

        Or raises one of notifications.exceptions:
            ProviderConfigurationError - missing/invalid settings, never retry
            ProviderPermanentError     - rejected message, never retry
            ProviderTemporaryError     - transient failure, safe to retry
        """

        raise NotImplementedError

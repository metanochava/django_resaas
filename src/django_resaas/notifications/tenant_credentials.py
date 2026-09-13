"""Per-tenant provider credential resolution.

get_provider_for_entity() is what NotificationProviderRegistry.get()
becomes when a tenant might have their own account (e.g. a hospital's
own WhatsApp Business number) instead of the platform-wide default -
identical to calling NotificationProviderRegistry.get(channel, name)
directly when entity_id is None or the tenant has no active override,
so every existing caller is unaffected.
"""

from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers import NotificationProviderRegistry

_PROVIDER_CLASSES = {}


def _provider_class_for(channel, provider_name):
    if not _PROVIDER_CLASSES:
        from django_resaas.notifications.providers.firebase import FirebasePushProvider
        from django_resaas.notifications.providers.sms import SMSProvider
        from django_resaas.notifications.providers.whatsapp import WhatsAppProvider

        _PROVIDER_CLASSES.update({
            (Channel.SMS, "twilio"): SMSProvider,
            (Channel.WHATSAPP, "meta_cloud_api"): WhatsAppProvider,
            (Channel.PUSH, "firebase"): FirebasePushProvider,
        })

    return _PROVIDER_CLASSES.get((channel, provider_name))


def get_provider_for_entity(channel, *, entity_id=None, branch_id=None, provider_name=None):
    """Resolution order: an active branch-specific override, then an
    active entity-wide override (branch=null), then the platform-wide
    default from NotificationProviderRegistry (env vars). `provider_name`,
    when given (a rule's explicit provider override), is matched
    against the credential row too - a tenant override for a different
    provider than the one requested is not used."""

    if entity_id is not None:
        from django_resaas.notifications.models import NotificationProviderCredential

        qs = NotificationProviderCredential.objects.filter(
            entity_id=entity_id, channel=channel, is_active=True,
        )
        if provider_name:
            qs = qs.filter(provider_name=provider_name)

        credential = None
        if branch_id is not None:
            credential = qs.filter(branch_id=branch_id).first()
        if credential is None:
            credential = qs.filter(branch__isnull=True).first()

        if credential is not None:
            provider_class = _provider_class_for(channel, credential.provider_name)
            if provider_class is not None:
                return provider_class(credentials=credential.get_config())

    return NotificationProviderRegistry.get(channel, provider_name)

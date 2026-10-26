"""Per-tenant provider credential resolution.

get_provider_for_entity() is what NotificationProviderRegistry.get()
becomes when a tenant might have their own account (e.g. a hospital's
own WhatsApp Business number) instead of the platform-wide default -
identical to calling NotificationProviderRegistry.get(channel, name)
directly when there is neither a tenant override nor a platform default
row (entity=null), so every existing caller is unaffected.
"""

from django_resaas.notifications.enums import Channel
from django_resaas.notifications.providers import NotificationProviderRegistry

_PROVIDER_CLASSES = {}


def _provider_class_for(channel, provider_name):
    if not _PROVIDER_CLASSES:
        from django_resaas.notifications.providers.email import EmailProvider
        from django_resaas.notifications.providers.firebase import FirebasePushProvider
        from django_resaas.notifications.providers.sms import SMSProvider
        from django_resaas.notifications.providers.whatsapp import WhatsAppProvider

        _PROVIDER_CLASSES.update({
            (Channel.EMAIL, "django"): EmailProvider,
            (Channel.SMS, "twilio"): SMSProvider,
            (Channel.WHATSAPP, "meta_cloud_api"): WhatsAppProvider,
            (Channel.PUSH, "firebase"): FirebasePushProvider,
        })

    return _PROVIDER_CLASSES.get((channel, provider_name))


def _provider_from(credential):
    provider_class = _provider_class_for(credential.channel, credential.provider_name)
    if provider_class is None:
        return None
    return provider_class(credentials=credential.get_config())


def get_provider_for_entity(channel, *, entity_id=None, branch_id=None, provider_name=None):
    """Resolution order: an active branch-specific override, then an
    active entity-wide override (branch=null), then the active platform
    default row (entity=null), then the platform-wide default from
    NotificationProviderRegistry (env vars). `provider_name`, when given
    (a rule's explicit provider override), is matched against the
    credential rows too - a row for a different provider than the one
    requested is not used."""

    from django_resaas.notifications.models import NotificationProviderCredential

    qs = NotificationProviderCredential.objects.filter(channel=channel, is_active=True)
    if provider_name:
        qs = qs.filter(provider_name=provider_name)

    candidates = []
    if entity_id is not None:
        if branch_id is not None:
            candidates.append(qs.filter(entity_id=entity_id, branch_id=branch_id))
        candidates.append(qs.filter(entity_id=entity_id, branch__isnull=True))
    candidates.append(qs.filter(entity__isnull=True))

    for candidate in candidates:
        credential = candidate.first()
        if credential is not None:
            provider = _provider_from(credential)
            if provider is not None:
                return provider

    return NotificationProviderRegistry.get(channel, provider_name)

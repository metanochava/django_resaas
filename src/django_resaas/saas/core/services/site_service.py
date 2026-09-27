"""Public sites: which Entity a site belongs to, and the messages its visitors
send through the contact form.

The Entity always comes from the request Origin (the site the browser is on)
matched against Entity.site - never from the request body. A client that
forges the Origin can only reach the contact form of that Entity's own site,
which is public anyway; the per-address throttle on the endpoint limits abuse.
"""
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import Q

from django_resaas.saas.core.events import EventDispatcher
from django_resaas.saas.models.address import Address
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.site_contact_message import SiteContactMessage

CONTACT_MESSAGE_RECEIVED = "site.contact_message.received"


def site_host(origin):
    """host[:port] of an Origin header, or "" when there is none."""
    return urlparse(origin or "").netloc


def entity_for_origin(origin, queryset=None):
    """The Entity whose `site` is this Origin, or None.

    Entity.site is a URLField stored WITH its scheme (e.g.
    "http://clinicaamal.co.mz") - but not consistently: existing rows use
    http even for sites served over https, and not every row has the same
    trailing slash. Match on host[:port] only, accepting either scheme and
    an optional trailing slash.
    """
    netloc = site_host(origin)
    if not netloc:
        return None

    return (
        (queryset if queryset is not None else Entity.objects.all())
        .filter(
            Q(site=f"http://{netloc}") | Q(site=f"http://{netloc}/") |
            Q(site=f"https://{netloc}") | Q(site=f"https://{netloc}/")
        )
        .first()
    )


def receive_contact_message(entity, origin, data):
    """Store the message and emit `site.contact_message.received`.

    Delivery (email / SMS / WhatsApp to the Entity's staff) is decided by
    django_resaas.notifications rules for that event, inside the same
    transaction (NotificationOutbox) - this function never sends anything.
    """
    with transaction.atomic():
        message = SiteContactMessage.objects.create(
            entity=entity,
            site=site_host(origin),
            name=data["name"],
            phone=data.get("phone") or None,
            email=data.get("email") or None,
            message=data["message"],
        )

        EventDispatcher.emit(
            CONTACT_MESSAGE_RECEIVED,
            instance=message,
            entity_id=entity.id,
            context={
                "name": message.name,
                "phone": message.phone or "",
                "email": message.email or "",
                "message": message.message,
                "site": message.site,
            },
        )

    return message


def public_branches(entity):
    """The Entity's branches for its public site's map: name, description
    and the main address (Branch AddressMixin) - full address and
    coordinates, None when not recorded. Nothing else about the branch."""
    result = []
    for branch in Branch.objects.filter(entity_id=entity.id).prefetch_related("addresses").order_by("name"):
        # the main address from the prefetched rows (branch.address would query again)
        address = next((a for a in branch.addresses.all() if a.address_type == Address.AddressType.MAIN), None)
        result.append({
            "id": str(branch.id),
            "name": branch.name,
            "description": branch.description or None,
            "address": address.full_address if address else None,
            "coordinates": address.coordinates if address else None,
        })
    return result

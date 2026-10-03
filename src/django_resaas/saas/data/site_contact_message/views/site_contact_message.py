from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services import site_service
from django_resaas.saas.data.site_contact_message.serializers.site_contact_message import (
    SiteContactMessageInputSerializer,
    SiteContactMessageSerializer,
)
from django_resaas.saas.models.site_contact_message import SiteContactMessage
from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin


class SiteContactThrottle(SimpleRateThrottle):
    """Per client address, signed in or not (a public form is spammed by
    address). settings.RESAAS_SITE_CONTACT_THROTTLE_RATE, default 5/hour."""

    scope = "site_contact"

    def get_rate(self):
        return getattr(settings, "RESAAS_SITE_CONTACT_THROTTLE_RATE", "5/hour")

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class SiteReadThrottle(SiteContactThrottle):
    """Reads of a public site (per client address): RESAAS_SITE_READ_THROTTLE_RATE,
    default 300/hour."""

    scope = "site_read"

    def get_rate(self):
        return getattr(settings, "RESAAS_SITE_READ_THROTTLE_RATE", "300/hour")


class SiteBranchesAPIView(APIView):
    """GET site/branches/  -> [{id, name, description, address, coordinates}]

    PUBLIC (explicit): the branches of the site's Entity for its map. The
    Entity comes from the request Origin (never from the query); throttled
    per client address. Only name, description and the main address.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (SiteReadThrottle,)

    def get(self, request):
        entity = site_service.entity_for_origin(request.headers.get("Origin"))
        if entity is None:
            raise ResaasAPIException(
                "This site is not linked to any organisation.",
                code="site_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(site_service.public_branches(entity))


class SiteContactAPIView(ResaasResponseMixin, APIView):
    """POST site/contact/  {name, phone?, email?, message}

    PUBLIC (explicit): the contact form of an Entity's public site, sent by
    visitors who have no session. The Entity comes from the request Origin
    (site_service.entity_for_origin), never from the body. Throttled per
    client address (429). The message is stored and
    `site.contact_message.received` is emitted; notifications rules decide
    who is told and how.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (SiteContactThrottle,)

    def post(self, request):
        origin = request.headers.get("Origin")
        entity = site_service.entity_for_origin(origin)
        if entity is None:
            raise ResaasAPIException(
                "This site is not linked to any organisation.",
                code="site_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = SiteContactMessageInputSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # a filled honeypot is a bot: answer like a success, store nothing
        if not serializer.validated_data.get("website"):
            site_service.receive_contact_message(entity, origin, serializer.validated_data)

        return Response({"received": True}, status=status.HTTP_201_CREATED)


@registerView("sitecontactmessages")
class SiteContactMessageAPIView(BaseAPIView):
    """Staff: the messages of their Entity (entity scope from the signed
    context; there is no Branch). They are created only by the public form,
    so creating one here is 405; staff mark them handled with a PATCH."""

    serializer_class = SiteContactMessageSerializer
    queryset = SiteContactMessage.objects.all()
    lookup_field = "id"

    def create(self, request, *args, **kwargs):
        # only the public form creates messages (restore etc. stay available)
        raise MethodNotAllowed(request.method)

    def perform_update(self, serializer):
        instance = serializer.instance
        new_status = serializer.validated_data.get("status", instance.status)

        extra = {}
        if new_status != instance.status:
            handled = new_status == SiteContactMessage.STATUS_HANDLED
            extra = {
                "handled_at": timezone.now() if handled else None,
                "handled_by": self.request.user if handled else None,
            }

        serializer.save(updated_by=self.request.user, **extra)

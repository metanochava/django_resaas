from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from django_resaas.engine.core.base.views import BaseAPIView, register_view
from django_resaas.engine.core.decorators.action import resaas_action

from django_resaas.notifications.enums import OutboxStatus
from django_resaas.notifications.exceptions import InvalidTransitionError
from django_resaas.notifications.models import NotificationOutbox
from django_resaas.notifications.serializers import NotificationOutboxSerializer

_CANCELLABLE_STATUSES = {
    OutboxStatus.PENDING,
    OutboxStatus.RETRY,
    OutboxStatus.DISPATCHING,
    OutboxStatus.QUEUED,
}


@register_view("outbox", module="notifications")
class NotificationOutboxAPIView(BaseAPIView):
    """Read-only for almost everything (spec section 78): no generic
    create/update/partial_update/destroy - the only way to change a row's
    status through this API is the `retry`/`cancel` actions below, both
    permission-gated and both validated through the same status machine
    (assert_transition) the worker itself uses."""

    queryset = NotificationOutbox.objects.all()
    serializer_class = NotificationOutboxSerializer

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @resaas_action(detail=True, methods=["post"])
    def retry(self, request, *args, **kwargs):
        """Manual retry - only ever valid from `failed` (spec section 61:
        never allow altering status via a generic PATCH; this is the one
        explicit, permission-checked door back in)."""

        outbox = self.get_object()

        try:
            outbox.transition(OutboxStatus.PENDING, next_retry_at=None, last_error=None)
        except InvalidTransitionError:
            return Response(
                {"detail": f"Cannot retry an outbox in status={outbox.status!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outbox.save(
            update_fields=["status", "next_retry_at", "last_error", "updated_at"]
        )

        transaction.on_commit(lambda: _dispatch(outbox.id))

        return Response(NotificationOutboxSerializer(outbox).data)

    @resaas_action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        """Only pre-send statuses can be cancelled - a `sent` row can
        never be retroactively cancelled (spec section 59)."""

        outbox = self.get_object()

        if outbox.status not in _CANCELLABLE_STATUSES:
            return Response(
                {"detail": f"Cannot cancel an outbox in status={outbox.status!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outbox.transition(OutboxStatus.CANCELLED)
        outbox.save(update_fields=["status", "updated_at"])

        return Response(NotificationOutboxSerializer(outbox).data)


def _dispatch(outbox_id):
    from django_resaas.notifications.outbox_dispatcher import OutboxDispatcher

    OutboxDispatcher.try_dispatch(outbox_id)

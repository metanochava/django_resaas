"""
OutboxDispatcher - claims NotificationOutbox rows and enqueues the
Celery task. Never calls a provider itself (spec section 29).

Claim strategy: a single, atomic, conditional UPDATE
(`.filter(status=old).update(status=new)`), never a
`if row.status == "pending"` read-then-write. This is correct on every
database this project runs on - SQLite (tests) included - without
needing SELECT ... FOR UPDATE: the UPDATE statement itself is atomic at
the database level, so two concurrent callers racing on the same row
will only ever have one succeed (return rowcount 1); the loser sees
rowcount 0 and backs off silently. See the plan's "OutboxDispatcher"
section for why this - rather than select_for_update(skip_locked=True) -
is the primary claim mechanism (that's reserved for the *batch
selection* step in recovery, where it's a pure efficiency optimization
on Postgres, with a portable fallback on SQLite).
"""

import logging

from django.conf import settings
from django.db import connection
from django.utils import timezone

from django_resaas.notifications.enums import OutboxStatus

logger = logging.getLogger("django_resaas.notifications")


class OutboxDispatcher:

    # =========================================================
    # FAST PATH - called from transaction.on_commit()
    # =========================================================

    @classmethod
    def try_dispatch(cls, outbox_id):
        """Best-effort, low-latency dispatch attempt. If this never runs
        (process crash right after commit) or fails (broker down), the
        row is left in a state periodic recovery will find - it is never
        the only way an outbox row gets processed."""

        from django_resaas.notifications.models import NotificationOutbox

        claimed = NotificationOutbox.objects.filter(
            id=outbox_id,
            status__in=[OutboxStatus.PENDING, OutboxStatus.RETRY],
        ).update(status=OutboxStatus.DISPATCHING, dispatching_at=timezone.now())

        if not claimed:
            return  # already claimed by someone else, or not eligible

        cls._enqueue_or_release(outbox_id)

    @classmethod
    def _enqueue_or_release(cls, outbox_id):
        from django_resaas.notifications.models import NotificationOutbox
        from django_resaas.notifications.tasks import process_notification

        try:
            process_notification.delay(str(outbox_id))
        except Exception:
            # Broker unreachable (or Celery not configured at all): never
            # leave the row stuck in "dispatching" - release it back so
            # the row stays recoverable (spec sections 28/68).
            logger.warning(
                "OutboxDispatcher: failed to enqueue outbox %s, releasing to pending",
                outbox_id,
                exc_info=True,
            )
            NotificationOutbox.objects.filter(
                id=outbox_id, status=OutboxStatus.DISPATCHING
            ).update(status=OutboxStatus.PENDING, dispatching_at=None)
            return

        NotificationOutbox.objects.filter(
            id=outbox_id, status=OutboxStatus.DISPATCHING
        ).update(status=OutboxStatus.QUEUED, queued_at=timezone.now())

    # =========================================================
    # BATCH SELECTION - periodic recovery (tasks.dispatch_pending_notifications)
    # =========================================================

    @classmethod
    def dispatch_eligible_batch(cls, batch_size=None):
        """Finds pending/retry rows eligible right now (scheduled_at/
        next_retry_at <= now) and tries to dispatch each. Returns how
        many were actually claimed+enqueued."""

        from django_resaas.notifications.models import NotificationOutbox

        batch_size = batch_size or getattr(
            settings, "NOTIFICATION_OUTBOX_BATCH_SIZE", 100
        )
        now = timezone.now()

        eligible_ids = cls._select_eligible_ids(NotificationOutbox, now, batch_size)

        for outbox_id in eligible_ids:
            # try_dispatch() does its own atomic conditional UPDATE, so a
            # row already claimed by the fast path (or another recovery
            # run) between selection and here is simply skipped.
            cls.try_dispatch(outbox_id)

        return len(eligible_ids)

    @staticmethod
    def _select_eligible_ids(model, now, batch_size):
        from django.db.models import Q

        base_qs = model.objects.filter(
            Q(status=OutboxStatus.PENDING) | Q(status=OutboxStatus.RETRY),
            scheduled_at__lte=now,
        ).filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now))

        # Postgres: lock+skip the batch while reading, so two recovery
        # runs (or a recovery run racing the fast path) never pick the
        # same rows. SQLite (tests): plain read - correctness still comes
        # from the atomic conditional UPDATE in try_dispatch(), this only
        # affects batch-selection efficiency, not safety.
        if connection.features.has_select_for_update_skip_locked:
            with connection.cursor():
                ids = list(
                    base_qs.select_for_update(skip_locked=True)
                    .order_by("priority", "scheduled_at")[:batch_size]
                    .values_list("id", flat=True)
                )
        else:
            ids = list(
                base_qs.order_by("priority", "scheduled_at")[:batch_size].values_list(
                    "id", flat=True
                )
            )

        return ids

    # =========================================================
    # STUCK RECOVERY
    # =========================================================

    @classmethod
    def recover_stuck(cls):
        """Finds rows stuck in `dispatching`/`processing` past their
        timeout and returns them to a recoverable state. Distinguishes
        "the worker/dispatcher process actually died" from "the provider
        is just slow" only by elapsed time (OUTBOX_DISPATCH_TIMEOUT /
        OUTBOX_PROCESSING_TIMEOUT) - a genuinely slow provider call within
        that window is not touched."""

        from django_resaas.notifications.models import NotificationOutbox

        now = timezone.now()

        dispatch_timeout = getattr(settings, "OUTBOX_DISPATCH_TIMEOUT", 300)
        processing_timeout = getattr(settings, "OUTBOX_PROCESSING_TIMEOUT", 300)

        dispatching_cutoff = now - timezone.timedelta(seconds=dispatch_timeout)
        processing_cutoff = now - timezone.timedelta(seconds=processing_timeout)

        recovered = NotificationOutbox.objects.filter(
            status=OutboxStatus.DISPATCHING, dispatching_at__lte=dispatching_cutoff
        ).update(status=OutboxStatus.PENDING, dispatching_at=None)

        recovered += NotificationOutbox.objects.filter(
            status=OutboxStatus.PROCESSING, processing_at__lte=processing_cutoff
        ).update(status=OutboxStatus.RETRY, processing_at=None, next_retry_at=None)

        return recovered

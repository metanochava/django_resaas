# Notifications (Email / SMS / WhatsApp)

A multi-tenant, asynchronous notification engine built into the framework
(`django_resaas.notifications`) — not a feature of any one business app.
Business code emits an event; the engine resolves rules, conditions,
recipients, preferences and a template; a durable `NotificationOutbox`
row is created in the same database transaction as the business change
that triggered it; a Celery worker delivers it later, off the request
path.

```text
Business event
  -> EventDispatcher.emit()
  -> NotificationEngine (rules -> conditions -> recipient -> preferences -> template)
  -> NotificationOutbox.objects.get_or_create(...)   # inside the caller's transaction
COMMIT
  -> fast dispatch (transaction.on_commit)     -> Queue -> Worker -> Provider -> DeliveryAttempt
  -> periodic recovery (Celery Beat, always)   -> Queue -> Worker -> Provider -> DeliveryAttempt
```

**The Outbox row in the database is the source of truth, not the queue.**
If Celery/Redis is offline when `on_commit` tries to enqueue, the row is
released back to `pending` and periodic recovery picks it up later — the
business transaction that created it is never affected either way.

## Opt-in by default — nothing sends until every layer says yes

- `NOTIFICATIONS_ENABLED` (settings, default `False`) — the system kill switch.
- A `NotificationSettings` row for the entity/branch, with the specific channel's
  `email_enabled`/`sms_enabled`/`whatsapp_enabled` set `True`. No row at all means off.
- The rule's own `module` must be an **active** `EntityApp` for that entity — the same
  module-activation check every other resource in this framework already uses (see
  [View registry](../architecture/registry.md)).
- The `NotificationRule` itself must have `enabled=True` (defaults to `False`).
- `category="marketing"` additionally requires an explicit `NotificationPreference(enabled=True)`
  row for that exact recipient/channel — absence means "do not send", never an implicit yes.
  Every other category defaults to allowed, but an explicit `enabled=False` preference
  (an opt-out) is always respected regardless of category.

A configured provider (env vars present) does **not** imply a channel is active — that's a
separate, explicit `NotificationSettings` flag.

## Quick start — your first rule

One `python manage.py shell` session against a tenant that already exists (an
`Entity`/`Branch`, plus an active `EntityApp` for whatever `module` you use below — see
[Creating a resource](../development/creating-resource.md) if you don't have one yet).
Nothing sends until the very last step, because every layer defaults to off:

```python
from django_resaas.notifications.models import (
    NotificationRule, NotificationTemplate, NotificationSettings,
)
from django_resaas.notifications.enums import Channel, Category

# 1. Turn the channel on for this entity — no row at all means the channel is off.
NotificationSettings.objects.create(entity=entity, email_enabled=True)

# 2. The rule — enabled=True has to be passed explicitly, it defaults to False.
rule = NotificationRule.objects.create(
    entity=entity,
    event="sales.sale.confirmed",
    module="sales",                              # checked against EntityApp, like any other resource
    channel=Channel.EMAIL,
    category=Category.TRANSACTIONAL,
    enabled=True,
    recipient_strategy="field_path",
    recipient_config={"field_path": "customer"},  # reads sale.customer
)

# 3. A template (language=None is this rule's default/fallback template).
NotificationTemplate.objects.create(
    rule=rule,
    subject="Sale {{ sale_number }} confirmed",
    body="Hi {{ recipient.email }}, your sale {{ sale_number }} for {{ total }} is confirmed.",
)
```

Then emit the event exactly as real business code would (see
[Emitting a business event](#emitting-a-business-event) for what `instance=` does here):

```python
from django.db import transaction
from django_resaas.core.events import EventDispatcher

with transaction.atomic():
    EventDispatcher.emit(
        "sales.sale.confirmed",
        instance=sale,
        context={"total": str(sale.total), "sale_number": sale.number},
    )
```

With `NOTIFICATIONS_ENABLED=True` and a Celery worker running, that's it. Without a worker
running yet, inspect the row it created directly:

```python
from django_resaas.notifications.models import NotificationOutbox

NotificationOutbox.objects.filter(event="sales.sale.confirmed").values(
    "status", "recipient_identity", "subject", "attempts"
)
```

## Emitting a business event

`django_resaas` core never imports business models — `EventDispatcher` only ever sees an event
name, a tenant, an actor, a serializable object reference and a context dict:

```python
from django_resaas.core.events import EventDispatcher

with transaction.atomic():
    sale = SaleService.confirm(...)

    EventDispatcher.emit(
        "sales.sale.confirmed",
        instance=sale,          # entity_id/branch_id/object-ref derived from it, then discarded
        actor=request.user,
        context={"total": str(sale.total), "sale_number": sale.number},
    )
# COMMIT — the NotificationOutbox (if any rule matched) was created above, inside this
# transaction, and rolls back with it if anything after emit() raises.
```

`emit()` runs **synchronously, in-process** — it is not a queue. Any registered listener
(the `NotificationEngine` is one; audit trails/webhooks/analytics can register their own
without touching this app — see `EventDispatcher.register(pattern, listener)`) that raises
is logged and does not propagate, so a bug in one listener never breaks the business
transaction that emitted the event.

## Rules, conditions, recipients, preferences, templates

A `NotificationRule` wires one `(entity, event, channel)` to a recipient strategy and,
optionally, a `conditions` tree:

```json
{
  "all": [
    {"field": "total", "operator": ">=", "value": 10000},
    {"field": "object.status", "operator": "==", "value": "confirmed"}
  ]
}
```

Operators: `==`, `!=`, `>=`, `>`, `<=`, `<`, `in`, `not_in`, `is_null`, `is_not_null`. No
`eval`/`exec` — see `notifications/conditions.py`. Any field-path segment starting with `_`
(`__class__`, `__dict__`, `__mro__`, `__globals__`, ...) is rejected outright; an unknown
operator or missing field evaluates to `False`, never raises.

`recipient_strategy` looks up `RecipientResolverRegistry`. Built in: `actor`, `object_owner`
/`field_path` (reads `recipient_config["field_path"]` off the resolved business object,
e.g. `"customer"`), `explicit` (`recipient_config["email"]`/`["phone"]`), `entity_admin`
(`Entity.admins`, the same relation `ResaasContextService` itself uses), `branch_admin`
(best-effort — see Limitations). Business apps register their own without touching this app:

```python
from django_resaas.notifications.recipients import Recipient, RecipientResolverRegistry

def resolve_customer(ctx):
    customer = ctx.obj.customer
    return [Recipient(type="customer", key=f"customer:{customer.id}", email=customer.email)]

RecipientResolverRegistry.register("sales.customer", resolve_customer)
```

`NotificationTemplate` (one per `(rule, language)`, `language=null` is the rule's default)
renders with the Django Template Engine and is **snapshotted onto the Outbox at creation
time** — editing a template later never changes an Outbox row already created from it, and
the worker never re-renders.

## The Outbox, the dispatcher, the worker, recovery

`NotificationOutbox` states: `pending -> dispatching -> queued -> processing -> sent`, with
`processing -> retry -> dispatching` on a transient failure, and a manual `failed -> pending`
door for the `retry` action. Transitions are centralized in
`NotificationOutbox.transition()`/`assert_transition()` — `sent -> processing` (or any other
undeclared transition) always raises.

**Claiming** a row is a single atomic conditional `UPDATE ... WHERE status IN (...)` — correct
on SQLite and Postgres alike without `SELECT ... FOR UPDATE`; a losing concurrent claim simply
affects 0 rows. Batch *selection* for periodic recovery uses
`select_for_update(skip_locked=True)` on Postgres (feature-detected) purely as an efficiency
optimization; SQLite falls back to a plain read, since the actual concurrency guarantee comes
from the per-row atomic UPDATE either way.

- `OutboxDispatcher.try_dispatch(id)` — the fast path, called from `transaction.on_commit()`.
  Claims the row, tries `process_notification.delay(id)`; if the broker is unreachable, releases
  the row back to `pending` instead of leaving it stuck.
- `dispatch_pending_notifications` (Celery Beat) — finds `pending`/`retry` rows whose
  `scheduled_at`/`next_retry_at` are due, in batches of `NOTIFICATION_OUTBOX_BATCH_SIZE`. This
  is the real guarantee: it runs whether or not the fast path ever fired.
- `recover_stuck_notifications` (Celery Beat) — returns rows stuck in `dispatching`/`processing`
  past `OUTBOX_DISPATCH_TIMEOUT`/`OUTBOX_PROCESSING_TIMEOUT` back to `pending`/`retry`.
- `process_notification(outbox_id)` (worker) — never reconstructs the business object; loads the
  Outbox, claims it, resolves the provider via `NotificationProviderRegistry`, calls
  `provider.send(...)`, records a `NotificationDeliveryAttempt`, and updates the Outbox. Exits
  immediately (a no-op) if the row is already `sent`/`cancelled` — safe under at-least-once
  redelivery.

Retries use exponential backoff with jitter (`OUTBOX_RETRY_BASE_SECONDS * 2**attempts`, capped
at `OUTBOX_RETRY_MAX_SECONDS`) up to `OUTBOX_MAX_ATTEMPTS`. Invalid email/E.164 phone, a missing
provider, or a `ProviderPermanentError`/`ProviderConfigurationError` all fail immediately with no
retry; timeouts/connection errors/429/5xx are treated as transient.

## Worked example, step by step

The same flow as Quick Start, spelled out at the level of what actually happens where —
useful when something doesn't fire and you need to know which step to check:

1. `SaleService.confirm(...)` changes business state, still inside `transaction.atomic()`.
2. `EventDispatcher.emit("sales.sale.confirmed", instance=sale, ...)` runs synchronously,
   in-process — builds the serializable payload and calls every registered listener.
3. `NotificationEngine.on_event(payload)` (registered in `NotificationsConfig.ready()`) finds
   the matching, `enabled=True` `NotificationRule` for this `(entity, event)`.
4. `conditions` evaluated against the payload's context + resolved object — a `False` result
   stops here, no Outbox, no error.
5. `recipient_strategy` resolves one or more `Recipient`s; `NotificationSettings` (channel
   enabled?) and `NotificationPreference` (consent) are checked per recipient.
6. `NotificationTemplate` picked for the recipient's language and rendered — `subject`/`body`
   are now plain strings, not templates anymore.
7. `NotificationOutbox.objects.get_or_create(idempotency_key=..., defaults={...})` — still
   inside the same transaction as step 1.
8. `transaction.atomic()` exits → **COMMIT**. The sale and the Outbox row commit together, or
   neither does (see the rollback test in `test_outbox_transaction.py`).
9. `transaction.on_commit(...)` fires `OutboxDispatcher.try_dispatch(outbox.id)` — claims the
   row (`pending -> dispatching`) and calls `process_notification.delay(outbox.id)`.
10. The Celery worker picks up the task, claims `dispatching -> processing`, creates a
    `NotificationDeliveryAttempt`, calls `EmailProvider.send(...)`, and marks the row `sent`.

**Same scenario, Redis offline at step 9**: `try_dispatch()` catches the broker error,
releases the row back to `pending` instead of leaving it in `dispatching`, and returns —
`SaleService.confirm()` already returned 200 to the caller at step 8, unaffected either way.
Nothing happens until `dispatch_pending_notifications` (Celery Beat) next runs, finds the
`pending` row (`scheduled_at <= now`), and repeats steps 9–10 — normally within
`OUTBOX_RECOVERY_INTERVAL_SECONDS`, with no special-casing and no data loss.

## Scheduled notifications

`NotificationOutbox.scheduled_at` (default: now) is what both the fast path and periodic
recovery actually check before dispatching a row — a row with a future `scheduled_at` is
correctly left alone by `dispatch_pending_notifications` no matter how long a worker/Beat has
been idle, exactly as the "reminder for tomorrow morning" use case needs. Pass it straight to
`EventDispatcher.emit()`:

```python
from django.utils import timezone

EventDispatcher.emit(
    "saude.consulta.scheduled",
    instance=consulta,
    scheduled_at=consulta.datetime - timezone.timedelta(hours=24),  # remind 24h before
)
```

> [!NOTE]
> `scheduled_at` must be timezone-aware, same convention as any other Django datetime field.
> It travels through the event payload as an ISO string (never a live `datetime`, see
> [Emitting a business event](#emitting-a-business-event)) and is parsed back into the
> `NotificationOutbox` row `NotificationEngine` creates. Omit it and the row gets the model's
> own default — `now()` — exactly as before.

## Idempotency

`NotificationOutbox.idempotency_key` (unique) is
`{entity_id}:{rule_id}:{channel}:{recipient_key}:{occurrence_id}` — the same logical event
(same rule, same recipient, same occurrence) always resolves to the same row via
`get_or_create()`, whether `emit()` is accidentally called twice or a queue redelivers a task.
`occurrence_id` defaults to `{event}:{object_pk}` if the caller doesn't pass one explicitly;
pass your own for anything that needs a finer-grained notion of "this exact occurrence"
(e.g. a specific confirmation attempt). This is **durable at-least-once processing with
best-effort exactly-once delivery** — not a universal exactly-once guarantee, since not every
provider supports an idempotency key on its own API.

## Providers

`BaseNotificationProvider.send(recipient, subject, body, metadata, idempotency_key)` returns
`{"success", "provider_message_id", "provider_status", "raw"}` or raises
`ProviderConfigurationError`/`ProviderPermanentError`/`ProviderTemporaryError`. Registered by
channel+name in `NotificationProviderRegistry` — the engine/worker never import a concrete
provider directly, which is also how tests substitute `Fake*Provider`s.

- **Email** — `django.core.mail.EmailMultiAlternatives`, whatever `EMAIL_BACKEND` is already
  configured. No new dependency; swapping to SES/SendGrid/Mailgun only means changing
  `EMAIL_BACKEND`.
- **SMS** — Twilio, implemented with the stdlib (`urllib`) rather than the `twilio` SDK, so
  there's no new required dependency. `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_FROM_NUMBER`.
- **WhatsApp** — Meta WhatsApp Cloud API, also stdlib `urllib`.
  `WHATSAPP_CLOUD_API_TOKEN`/`WHATSAPP_CLOUD_API_PHONE_NUMBER_ID`/`WHATSAPP_CLOUD_API_VERSION`.
  `NotificationTemplate.provider_metadata`'s `provider_template_name`/`provider_language` sends a
  pre-approved template instead of free text.

> [!WARNING]
> None of these credentials are ever stored in the database, returned by the API, written to
> logs, or exposed in the Schema contract — env vars only.

## Settings reference

| Setting | Default | Purpose |
|---|---|---|
| `NOTIFICATIONS_ENABLED` | `False` | System-wide kill switch |
| `NOTIFICATION_OUTBOX_BATCH_SIZE` | `100` | Rows per recovery batch |
| `OUTBOX_RETRY_BASE_SECONDS` / `OUTBOX_RETRY_MAX_SECONDS` | `30` / `3600` | Backoff bounds |
| `OUTBOX_MAX_ATTEMPTS` | `5` | Attempts before `failed` |
| `OUTBOX_DISPATCH_TIMEOUT` / `OUTBOX_PROCESSING_TIMEOUT` | `300`s each | Stuck-row thresholds |
| `OUTBOX_RECOVERY_INTERVAL_SECONDS` | `30` | Suggested Beat interval |
| `NOTIFICATION_OUTBOX_RETENTION_DAYS` / `NOTIFICATION_ATTEMPT_RETENTION_DAYS` | `90` / `90` | `notification_cleanup` window |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | unset | Only used by this app |

## Wiring Celery + Beat in a host project

`django_resaas.notifications.tasks` uses `@shared_task`, so it binds to whatever Celery app the
host project creates — this framework doesn't ship one. `pip install django_resaas[notifications]`
for the `celery` dependency, then, in the host project (next to its `settings.py`):

```python
# yourproject/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yourproject.settings")
app = Celery("yourproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "notifications-dispatch-pending": {
        "task": "django_resaas.notifications.dispatch_pending_notifications",
        "schedule": 30.0,  # OUTBOX_RECOVERY_INTERVAL_SECONDS
    },
    "notifications-recover-stuck": {
        "task": "django_resaas.notifications.recover_stuck_notifications",
        "schedule": 60.0,
    },
    "notifications-cleanup": {
        "task": "django_resaas.notifications.cleanup_notifications",
        "schedule": 86400.0,  # daily
    },
}
```

```python
# yourproject/__init__.py
from .celery import app as celery_app
__all__ = ("celery_app",)
```

Add `"django_resaas.notifications"` to `INSTALLED_APPS` (same as `"hr"`), then run migrations,
a worker, and Beat:

```bash
python manage.py migrate
celery -A yourproject worker -l info
celery -A yourproject beat -l info
```

## Permissions, admin, REST API

Standard convention (`{prefix}_{model_name}`, see [Permissions](../security/permissions.md)):
`view/add/change/delete_notificationrule`, same for `template`/`preference`/`settings`.
`NotificationOutbox`/`NotificationDeliveryAttempt` only expose `view_*` — `create`/`update`/
`partial_update`/`destroy` return `405` on both ViewSets, so a generic `PATCH` can never mark a
row `sent` by hand. The only mutations are two permission-checked actions:
`POST .../outbox/<id>/retry/` (codename `retry_notificationoutbox`, only valid from `failed`)
and `POST .../outbox/<id>/cancel/` (codename `cancel_notificationoutbox`, only valid before
`sent`). Django Admin registers all six models; Outbox/DeliveryAttempt are read-only there too.

> [!TIP]
> The `retry`/`cancel` permissions are `@resaas_action`-managed, which means their
> `Permission` rows only get created once `ActionSyncService.sync_registry()` runs *after*
> `django_resaas.notifications.views` has actually been imported (populating
> `VIEW_REGISTRY`) — run `python manage.py sync_actions` once, after the app has started at
> least once (e.g. after first `runserver`/first request, so the URLconf has loaded), to
> create them; then grant them to whichever group should have them like any other permission
> — neither step is automatic, exactly like every other `@resaas_action` in this framework
> (see [View registry](../architecture/registry.md)).

`GET /api/notifications/catalog/` (plain `APIView`, additive, outside `ResaasSchemaBuilder`)
lists supported channels/categories/priorities and this entity's configured events — for a
future Quasar "Notification Settings" screen. Every model still gets its normal per-model
Schema 1.0 contract for free via `class RESAAS: crud = True` — nothing changed in the shared
schema builder.

### Endpoints

Routed exactly like every other autoloaded resource in this framework (`{module}/{name}/`,
`module="notifications"` passed explicitly to `@register_view` — see
[View registry](../architecture/registry.md)); prefix with wherever the host project mounts
`django_resaas.urls` (`/api/` in this framework's own dev project):

| Endpoint | Methods | Notes |
|---|---|---|
| `/api/notifications/rules/` | full CRUD | `NotificationRule` |
| `/api/notifications/templates/` | full CRUD | `NotificationTemplate` |
| `/api/notifications/preferences/` | full CRUD | `NotificationPreference` |
| `/api/notifications/settings/` | full CRUD | `NotificationSettings` |
| `/api/notifications/outbox/` | `GET` (list/retrieve) only | `NotificationOutbox` — 405 on write |
| `/api/notifications/outbox/<id>/retry/` | `POST` | `retry_notificationoutbox` permission, `failed` only |
| `/api/notifications/outbox/<id>/cancel/` | `POST` | `cancel_notificationoutbox` permission, pre-`sent` only |
| `/api/notifications/deliveryattempt/` | `GET` (list/retrieve) only | `NotificationDeliveryAttempt` |
| `/api/notifications/catalog/` | `GET` | channels/categories/priorities/configured events |

Example — create a rule (`POST /api/notifications/rules/`, same headers as any other
tenant-scoped request in this framework — `X-RESAAS-Context` + `L`, see
[Multi-tenancy](../architecture/multi-tenancy.md)):

```json
{
  "event": "sales.sale.confirmed",
  "module": "sales",
  "channel": "email",
  "category": "transactional",
  "enabled": true,
  "recipient_strategy": "field_path",
  "recipient_config": {"field_path": "customer"}
}
```

Example — retry a failed row (`POST /api/notifications/outbox/<id>/retry/`, empty body):

```json
{
  "id": "…", "status": "pending", "attempts": 2, "next_retry_at": null, "last_error": null
}
```

## Diagnosing and operating

```bash
python manage.py resaas_notifications_check   # never prints secrets
python manage.py notification_dispatch_pending
python manage.py notification_recover_stuck
python manage.py notification_cleanup
```

## Known limitations

- **`branch_admin` is best-effort.** The framework has no explicit "branch admin" role today
  (`BranchUser` carries no admin flag) — the built-in resolver looks up users holding a
  configurable permission (`recipient_config["permission"]`, default `"change_branch"`) via
  `BranchUserGroup`. Register your own resolver for anything more precise.
- **Language fallback is recipient -> `NotificationSettings.default_language` -> Django's
  `LANGUAGE_CODE`** — two guaranteed tiers, not three. `Entity` has no language field of its
  own in this framework; the entity-level default lives on the `NotificationSettings` row this
  app introduces instead of a new `Entity` field.
- **Channel fallback re-renders nothing.** `NotificationRule.fallback_channel` (off by default)
  reuses the original channel's rendered body/subject rather than re-selecting a template for
  the fallback channel — acceptable for SMS/WhatsApp fallback from a failed WhatsApp send, less
  so if the fallback channel genuinely needs different content.
- **`NotificationTemplate`'s `unique_together(rule, language)`** does not stop two rows with
  `language=null` for the same rule at the database level (SQL NULLs aren't equal in a unique
  constraint) — enforce "one default template per rule" at the application layer if this
  matters to you. The same caveat applies to `NotificationSettings`' `(entity, branch)`
  constraint for two entity-wide (`branch=null`) rows.
- **`NotificationRule.deduplication_key`** described in earlier design notes was scoped out —
  `idempotency_key` already provides the core duplicate-prevention guarantee; a
  still-true-while-condition-persists dedup window (e.g. "don't re-notify low stock on every
  save while it stays low") is a reasonable future addition, not implemented here.

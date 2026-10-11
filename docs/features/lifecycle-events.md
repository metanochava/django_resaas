# Model lifecycle events

**What.** The generic CRUD of `BaseAPIView` can announce what happened to a record —
`created`, `updated`, `deleted`, `restored`, `hard_deleted` — as an event
`"<app_label>.<model>.<action>"` (e.g. `saude.pedidoexamemedico.created`) on the existing
[`EventDispatcher`](notifications.md#emitting-a-business-event).

**Why.** A module can react to a write (generate a code, create related records, ask for a
notification) without overriding every view, and an administrator can attach a
[notification rule](notifications.md) to the event from the UI. It reuses the event,
notification, permission and tenant machinery that already exists; there is no second
action or rule engine.

Code: `saas/core/events/lifecycle.py` (opt-in, emit, `load_instance`, catalogue) and
`saas/core/base/views.py` (`perform_create`, `perform_update`, `perform_destroy`, `restore`,
`hard_delete`).

## Turning it on (per model)

Nothing is emitted unless the model opts in, in its `RESAAS` metadata:

```python
class PedidoExameMedico(BaseModel):
    class RESAAS:
        lifecycle_events = True                     # every action
        # lifecycle_events = ["created", "updated"] # only these
```

An unknown action name raises `ValueError` (a configuration error, not a silent no-op).

| Action | Emitted by | Context |
|---|---|---|
| `created` | `perform_create` (`POST /<model>s/`) | `{"lifecycle": "created"}` |
| `updated` | `perform_update` (`PUT`/`PATCH`) | `{"lifecycle": "updated", "fields": [<fields sent>]}` |
| `deleted` | `perform_destroy` (`DELETE`, soft delete) | `{"lifecycle": "deleted"}` |
| `restored` | `restore` action | `{"lifecycle": "restored"}` |
| `hard_deleted` | `hard_delete` action | `{"lifecycle": "hard_deleted"}` (the row is gone) |

The payload is the standard event payload: `event`, `entity_id`, `branch_id`, `actor_id`,
`object` `{app_label, model, pk}`, `context`, and an `occurrence_id` unique to **this** write
(two updates of the same record are two occurrences — notification idempotency keys use it).
Never a live model instance.

## Where it is emitted, and why there

Only from the API layer, not from `Model.save()` nor Django signals: those also run in the
shell, migrations, imports and whenever code saves again, which would repeat events and allow
loops. Consequences:

- a listener that writes through the ORM **does not** emit lifecycle events → no recursion;
- writes outside the generic CRUD (services, management commands, a view that overrides
  `perform_create` without calling `super()`) emit nothing — a service that owns a business
  transition emits its own business event (`EventDispatcher.emit("hr.employee.hired", ...)`).

## Programmatic actions (Python)

Register a listener, as for any event, from your app's `ready()`:

```python
# your_module/apps.py
from django.apps import AppConfig


class YourModuleConfig(AppConfig):
    name = "your_module"

    def ready(self):
        from django_resaas.saas.core.events import EventDispatcher
        from your_module.services.orders import on_order_created

        EventDispatcher.register("your_module.order.created", on_order_created, propagate=True)
```

```python
# your_module/services/orders.py
from django.db import transaction

from django_resaas.saas.core.events.lifecycle import load_instance


def on_order_created(payload):
    order = load_instance(payload)          # re-read, limited to the payload's tenant
    if order is None:
        return
    order.code = f"ORD-{order.pk.hex[:8].upper()}"
    order.save(update_fields=["code"])      # no new lifecycle event: no loop

    # an external effect only after the commit
    transaction.on_commit(lambda: print("order", order.pk, "committed"))
```

`load_instance(payload)` resolves `object` with `all_objects` (soft-deleted rows included),
filtered by the payload's `entity_id` (and `branch_id` when the model has one). It returns
`None` for another tenant's record, a payload without `entity_id` for a tenant model, or a row
that no longer exists.

## Transactions and failures

The write and the emit run in **one** `transaction.atomic()` block, the event right after the
write. Listeners run synchronously, in registration order (`register()` order; a pattern such
as `"demo.*"` matches like any other).

| Listener | When it raises |
|---|---|
| `register(..., propagate=True)` | the exception bubbles: the write is **rolled back** and the request fails (500 for an unexpected error; raise a DRF / RESAAS exception for a 4xx with the error contract) |
| `register(...)` (default) | logged (`django_resaas.events`), the other listeners still run, the write is **kept** |

- Effects that must succeed with the write (a code, related rows): `propagate=True`, done inside.
- External effects (messages, HTTP calls, files): `transaction.on_commit(...)`, or a
  notification rule (Outbox written in the transaction, sent by Celery after the commit). They
  never run for a rolled-back write.
- Exactly-once is **not** guaranteed for your own `on_commit` callbacks (a crash between commit
  and callback loses it). The notification Outbox is the durable path: unique
  `idempotency_key`, retries, recovery tasks.

## Configurable actions (administrators)

The configurable side is the existing **notification rules**: a `NotificationRule` may name a
lifecycle event (`event = "saude.pedidoexamemedico.created"`), with its tenant scope (Entity,
optional Branch), safe declarative `conditions` on the record (`object.<field>`, see
`notifications/conditions.py` — no `eval`, no SQL), recipients and templates. Rules are
managed through `NotificationRuleAPIView` (a `BaseAPIView`: per-action permissions, tenant
scope) and the quasar_resaas pages `pages/notifications/rule/`.

`GET /api/notifications/catalog/` returns `lifecycle_events`: the lifecycle event names of the
models that opted in, **for the modules active in the current Entity** — what a rule can be
attached to. Business events emitted by services are not listed (no registry of them); a rule
may still name one.

Configurable actions other than notifications (e.g. "create a related record" chosen in the UI)
do not exist: they would need a registry of named, parameterised actions and a tenant-scoped
rule model. That is a separate proposal, not implemented.

## Security and multi-tenancy

- `entity_id`, `branch_id` and `actor_id` come from the signed `X-RESAAS-Context` validated by
  `BaseAPIView.initial()`; tenant fields sent in the body are ignored (they are not editable).
- A request refused by authentication, context, module activation or permission never reaches
  the write: no event.
- Notification rules are selected by the event's `entity_id` (and branch), so another tenant's
  rule never fires.
- Listeners must re-read data with `load_instance(payload)` (or their own tenant-filtered query)
  and must not trust anything else in the payload as authorization.

## Limitations

- Synchronous and in-process: a slow listener slows the request. Put slow work behind
  `on_commit` + Celery or the notification Outbox.
- No `before_*` events: validation before a write belongs to the serializer's `validate()` or
  the domain service.
- Bulk operations (`QuerySet.update()`, `bulk_create`) emit nothing.

## Troubleshooting

| Symptom | Check |
|---|---|
| No event | the model has `RESAAS.lifecycle_events`; the write went through `BaseAPIView`'s generic CRUD (an override without `super()` skips it); the listener's pattern matches `<app_label>.<model_name>.<action>` (lowercase model name) |
| A notification rule does not fire | the rule's `module` is active for the Entity, `enabled=True`, a `NotificationSettings` row enables the channel, `NOTIFICATIONS_ENABLED` is on, its `conditions` match |
| The write is rolled back with a 500 | a `propagate=True` listener raised — see the `django_resaas.events` / server log |

Tests: `saas/tests/test_lifecycle_events.py`, `notifications/tests/test_lifecycle_rules.py`.

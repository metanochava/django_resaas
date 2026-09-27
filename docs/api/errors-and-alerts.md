# Errors and alerts

Every API exposed by `django_resaas` and by business modules built on `BaseAPIView` answers
failures and extra messages through the same two mechanisms: the **error** body and **alerts**.
This page documents the backend side of the contract; see
[quasar_resaas: Errors and alerts](https://github.com/metanochava/quasar_resaas/blob/main/docs/quasar-resaas/features/errors-and-alerts.md) for how the
frontend consumes it.

## The error body

A failed request answers, next to its HTTP status (never repeated in the body), with exactly one
top-level key:

```json
{"error": {"code": "group_already_assigned", "message": "This profile is already assigned.", "details": null}}
```

- `message` — always present; human text, translated with the request's language
  (`Translate.tdc`, see [translation architecture](https://github.com/metanochava/quasar_resaas/blob/main/docs/quasar-resaas/features/translation.md)).
- `code` — only when a caller must branch on this condition programmatically. Stable, technical,
  **never translated**. DRF's own generic codes (`"error"`, `"invalid"`) are never published as-is
  — see `GENERIC_CODES` in `saas/core/exceptions/handler.py`.
- `details` — structured extra data, `null` when there is none. For a validation error it is the
  `field -> [messages]` map, so a form can put each message on its own field.

The HTTP status is the single source of truth and is never repeated in the body — no `"status"`
key, no `"success": false`.

> [!NOTE]
> Until this contract's migration finished, the body also carried `{"detail": "...", "code": "..."}`
> at the top level (plus the bare `{"field": ["msg"]}` map for validation) as **DEPRECATED aliases**
> of `error`, kept for older consumers. Every consumer (`django_resaas`, `quasar_resaas`,
> `dev/front`, `pro/front`) has since been migrated onto `error`/`errorMessage()`/`errorCode()` (see
> the frontend page), so the aliases were **removed** rather than kept forever. A response with a
> top-level `detail` or `code` next to `error` is a regression — see
> `saas/tests/test_error_alert_contract.py::TestNoLegacyAliases`.

## `resaas_exception_handler`

`saas/core/exceptions/handler.py`'s `resaas_exception_handler` is the project's DRF
`EXCEPTION_HANDLER` (`REST_FRAMEWORK["EXCEPTION_HANDLER"]`) — every `rest_framework.exceptions.APIException`
raised anywhere in a view ends up shaped by it, without the view doing anything itself:

```python
raise ConflictError("This profile is already assigned.", code="group_already_assigned")
# -> 409 {"error": {"code": "group_already_assigned", "message": "...", "details": null}}
```

- Raise a DRF exception (`ValidationError`, `PermissionDenied`, `NotFound`, ...), `ApiResponse.fail(...)`,
  or a RESAAS exception (`ResaasAPIException`, `ConflictError` — `saas/core/exceptions/`). All of
  them end up in the same body through this one handler.
- A `ValidationError` (or any exception whose `.detail` is a dict/list) is treated as field
  validation: `message` becomes the generic `"Please correct the highlighted fields."`, and
  `details` carries the real per-field messages, translated in place (shape preserved, including
  nested dicts/lists).
- An exception raised with `{"code": ..., "detail": ...}` (a pattern some views already use, e.g.
  a stable `temporary_password_expired`) is treated as one error with that stable code, not as a
  field map.
- An **unexpected** exception (anything not an `APIException`) is logged in full on the server
  (`logger.exception`, includes the view class) and answered as a generic `500` — no traceback,
  SQL, path or value ever reaches the client. With `DEBUG=True`, the handler returns `None` so
  Django's own debug page is kept for local development.
- `settings.py` imports `django_resaas.saas.core.utils` **before** `REST_FRAMEWORK` is even
  defined; nothing reachable from that import chain may import `rest_framework.views` at module
  level (it would freeze DRF's `DEFAULT_AUTHENTICATION_CLASSES`/etc. for the whole process) — the
  handler imports `rest_framework.views.exception_handler` **inside** the function for this reason.
  See `TestSetupIsNotBroken` in the test file below.

## `error_response()` — building an answer by hand

A view that decides a failure itself (nothing was raised) uses `error_response()` from the same
module instead of hand-building a `Response`:

```python
from django_resaas.saas.core.exceptions import error_response

return error_response(request, "Nothing to export.", status_code=400, code="empty_export")
```

Same contract as an exception answer — `{"error": {...}}` only, `message` translated, `code`
untranslated.

## Alerts

Alerts are **extra** messages a request wants the user to see next to its normal result — they are
not the failure, and a failed request must not repeat its own error as an alert:

```json
{"id": 1, "alerts": [{"level": "warning", "message": "...", "code": "employee_without_profile", "details": null}]}
```

- `level` is one of `success | info | warning | error` (never Quasar's own `positive`/`negative`
  names — the frontend maps them, see the frontend page).
- `message` is required and translated; `code` and `details` are optional.

Produce them with `add_alert(request, message, level=..., code=...)`
(`saas/core/alerts.py`). They are queued **on the request** (never global state — each request gets
its own list) and merged into the JSON body by `ResaasResponseMixin`, already included in
`BaseAPIView` and `ExplicitAccessMixin`; add the mixin explicitly to any other `APIView` that needs
alerts. Only a **dict** payload can carry them (a bare list response is left untouched — see
`TestAlertsOnResponses::test_a_bare_list_payload_is_left_alone`). Success payloads are **not**
wrapped in a `"data"` key — alerts are purely additive, so existing consumers keep working
unchanged.

Business notifications (a contract about to expire, an order awaiting approval) are a different
concern and belong to `django_resaas.notifications`, not to alerts — see
[Notifications](../features/notifications.md).

## Multi-tenancy and security

This page only covers the shape of the response body. Every request still goes through the full
security chain before it can succeed or fail this way — see [BaseAPIView](base-api-view.md) and
[Multi-tenancy](../architecture/multi-tenancy.md). A `403` for a missing permission uses this same
`error` contract (`code: "permission_denied"` by default when a `fail()` call gives none).

## Tests

`saas/tests/test_error_alert_contract.py` is the source of truth for the exact behaviour documented
above — including the "no legacy alias leaks" regression tests
(`TestNoLegacyAliases`) and real-endpoint checks (`TestRealEndpoints`) that exercise the actual URL
routing, not just the handler function in isolation.

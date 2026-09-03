# Middleware

`django_resaas` ships three middleware classes under `django_resaas.core.middleware`. Only two are
enabled by default in the `src/dev` project's `MIDDLEWARE` setting.

## `TenantContextMiddleware` (`core/middleware/tenant.py`) - enabled by default

Runs on every request. Initializes `request.tenant_context`, `request.tenant_context_error`,
`request.entity_type_id`, `request.entity_id`, `request.branch_id`, `request.group_id` to `None`,
and `request.lang_id` from the `L` header. If an `X-RESAAS-Context` header is present, it decodes
it via `ResaasContextService.decode(token)` and populates `entity_type_id`/`entity_id`/
`branch_id`/`group_id` from the decoded payload; a decode failure is captured into
`request.tenant_context_error` rather than raising, so downstream code (permission checks,
queryset filtering - see [`docs/architecture/multi-tenancy.md`](multi-tenancy.md)) sees a
consistent (if empty) tenant context either way.

## `FileAccessMiddleware` (`core/middleware/file_access.py`) - enabled by default

Only acts on requests whose path starts with `settings.MEDIA_URL`. Requires a `?token=` query
parameter validated by `FullPath.validate_token(token)`; without a valid token it returns a `401`
JSON response (`{"alert_error": "..."}`). This is what protects direct access to uploaded media
files (see [`docs/features/files-pdf.md`](../features/files-pdf.md)).

## `FrontEndMiddleware` (`core/middleware/front_end.py`) - **not enabled by default**

Available but commented out in `src/dev/settings.py`'s `MIDDLEWARE` list. When enabled, it
restricts which registered "frontend" (`FrontEnd` model, identified by `FEK`/`FEP` header
credentials) may call which URL scope (`/api/<scope>/...`) and with which HTTP methods, based on
`DJANGO_REST_AUTH.FRONT_END` settings (`REQUIRE_CREDENTIALS`, `PUBLIC_URL`, `URL_RULES`):

- If `REQUIRE_CREDENTIALS` is falsy, the middleware only enforces the public/scope rules below and
  never requires `FEK`/`FEP`.
- Otherwise, every request needs valid `FEK`/`FEP` headers matching a `FrontEnd` row, unless its
  URL scope is listed in `FRONT_END.PUBLIC_URL`.
- `frontend.access` (`super`, `read`, `readwrite`, `write`) gates both the URL scope (against
  `FRONT_END.URL_RULES`) and the HTTP method allowed for that access level.

> [!WARNING]
> Known issue: the commented-out entry in `src/dev/settings.py` references
> `django_resaas.core.middleware.frontend.FrontEndMiddleware` (no underscore), but the real
> module is `django_resaas.core.middleware.front_end` (with an underscore). Uncommenting
> that line as written would raise `ModuleNotFoundError` - the dotted path needs the
> underscore added before this middleware can actually be enabled.

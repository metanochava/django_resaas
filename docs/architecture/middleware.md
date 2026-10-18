# Middleware

`django_resaas` ships three middleware classes under `django_resaas.saas.core.middleware`. Only two are
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
parameter validated by `FullPath.validate_token(token, request.path)` - the token must have been
issued for that exact path. Without one it returns `401` in the error contract
(`{"error": {"message": ..., "code": "file_token_invalid", "details": null}}`). With
`FILE_TOKEN.X_ACCEL_REDIRECT` set, a valid request is answered with an `X-Accel-Redirect` so the
web server sends the file. This is what protects direct access to uploaded media files - only
when the web server sends `/media/` to Django (see
[`docs/features/files-pdf.md`](../features/files-pdf.md#serving-the-file-web-server)).

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

- Refusals answer `401` (missing or unknown credentials) or `403` (scope or method not allowed)
  in the error contract (`{"error": {"message": ..., "details": null}}`), like every other failed
  request. Before the release after 0.0.659 they used the deprecated
  `{"code": 10001 | 10003, "alert_error": ...}` shape.
- The commented-out entry in `src/dev/settings.py` is the real dotted path; uncomment it to try
  the gate in the demo project.

> [!IMPORTANT]
> **`FEK`/`FEP` are not secrets and are not authorization.** A browser frontend sends both headers
> on every request (`quasar_resaas` `services/api.js` reads `process.env.FRONT_END_KEY` /
> `FRONT_END_PASSWORD`), so their values are compiled into the public JavaScript bundle and
> anyone who opens the site can read them. The gate only identifies *which kind of client* is
> calling and narrows the URL scopes and HTTP methods it may use; it grants nothing by itself.
> Every protected operation still needs authentication, the signed tenant context and its
> permission (see [Permissions](../security/permissions.md)). Never use a `FrontEnd` access
> level (`super` included) as a reason to skip those checks, and never give a `FEP` to a server
> integration expecting it to stay confidential.

### Troubleshooting: the gate seems to do nothing

`REQUIRE_CREDENTIALS` is read from the project's `DJANGO_REST_AUTH.FRONT_END` setting. If the
project's `settings.py` fills it from an environment variable, check that the variable name in
`.env` is the one `settings.py` reads - a different name leaves it `None` (falsy) and the gate
off, silently.

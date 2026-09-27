# Public sites and their contact form

An Entity can have a public website (a clinic, a shop, ...) served by the same
frontend. The backend recognises which Entity a site belongs to from the browser
`Origin`, gives the site that Entity's look (`GET site/`), and receives the
messages visitors send through its contact form (`POST site/contact/`).

## Which Entity a site belongs to

`Entity.site` holds the site's URL (e.g. `http://clinicaamal.co.mz`).
`site_service.entity_for_origin(origin)` (`saas/core/services/site_service.py`)
matches the request `Origin` on `host[:port]` only: `http` or `https`, with or
without a trailing slash (existing rows are not consistent). Both endpoints below
use it; the Entity is **never** taken from the request body.

Business modules that expose their own public-site endpoints reuse the same
function and the same rules (Entity from the Origin, explicit `AllowAny`,
throttle per address, honeypot for forms) — e.g. the health module's online
booking (`saude/publicbooking/`, documented in that app).

`Entity.founded_on` (optional date) records when the organisation was
founded; public sites derive "years of experience" from it (the health
module's `saude/publicsite/stats/`). Migration: one nullable column
(backward compatible).

## `GET site/` — the site's settings

PUBLIC (`AllowAny`, listed in `PUBLIC_BY_DESIGN`). Returns the Entity
(`EntitySerializer`) and its theme, typography, layout and animation settings, each
falling back to the EntityType's. With an unknown Origin it answers
`{"Origin": "Desconhecida"}`.

## `GET site/branches/` — the branches for the site's map

PUBLIC (`AllowAny`, listed in `PUBLIC_BY_DESIGN`), `SiteBranchesAPIView`,
throttled per client address (`RESAAS_SITE_READ_THROTTLE_RATE`, default
`300/hour`). The Entity comes from the `Origin` (unknown → `404 site_not_found`).

```json
[{"id": "…", "name": "Sede", "description": null,
  "address": "Maputo, Moçambique", "coordinates": {"lat": -25.963974, "lng": 32.586694}}]
```

`address` / `coordinates` come from the Branch's **main** `Address`
(`AddressMixin`; 6 decimal places); both are `null` when the branch has no
address. Nothing else about the branch is returned. A site shows on its map
only the branches with coordinates (the Amal site: one map, a button per branch
when there are several). Record a branch's location in its form (address picker)
or with `branch.set_address(latitude=…, longitude=…, …)`.

## `POST site/contact/` — the contact form

PUBLIC (`AllowAny`, listed in `PUBLIC_BY_DESIGN`), `SiteContactAPIView`.

```http
POST /api/site/contact/
Origin: https://clinicaamal.co.mz

{"name": "Ana", "phone": "+258 84 000 0000", "email": "", "message": "I would like an appointment."}
```

| Field | Rule |
|---|---|
| `name` | required, up to 150 characters |
| `phone` / `email` | at least one of them (staff must be able to reply) |
| `message` | required, up to 2000 characters |
| `website` | honeypot: hidden in the form; when filled the answer is a normal `201` but nothing is stored |

| Status | When |
|---|---|
| `201 {"received": true}` | stored (or dropped by the honeypot) |
| `400` | validation; `error.details` has one list of messages per field (`phone` and `email` when both are empty) |
| `404 site_not_found` | the Origin matches no `Entity.site` |
| `429` | more than `RESAAS_SITE_CONTACT_THROTTLE_RATE` requests from the same client address (default `5/hour`) |

What happens (`site_service.receive_contact_message`, one transaction):

1. a `SiteContactMessage` row is created for the Entity, with the site host
   (`status="new"`);
2. the event **`site.contact_message.received`** is emitted through
   `EventDispatcher` with `context = {name, phone, email, message, site}` and the
   Entity as tenant (no Branch).

The endpoint never sends email itself. To be told about new messages, an Entity
creates a notifications rule for that event, e.g. an email to its admins:

```python
rule = NotificationRule.objects.create(
    entity=entity, event="site.contact_message.received", module="django_resaas",
    channel=Channel.EMAIL, category=Category.TRANSACTIONAL, enabled=True,
    recipient_strategy="entity_admin",
)
NotificationTemplate.objects.create(
    rule=rule,
    subject="New message from {{ name }} ({{ site }})",
    body="{{ name }} - {{ phone }} {{ email }}\n\n{{ message }}",
)
```

Every layer is opt-in (`NOTIFICATIONS_ENABLED`, `NotificationSettings`, the rule's
`enabled`) — see [Notifications](notifications.md).

### Security

- The Entity comes from the `Origin`. A client that forges the `Origin` can only
  send a message to the contact form of that Entity's own site, which is public
  anyway. The throttle (per client address, signed in or not) limits abuse.
- The visitor chooses no Entity, Branch or status; unknown body fields
  (`entity`, `entity_id`, ...) are ignored.

## Staff inbox — `sitecontactmessages/`

PROTECTED: `SiteContactMessageAPIView` (`BaseAPIView`, `@registerView`), at
`/api/django_resaas/sitecontactmessages/`.

| Operation | Permission | Notes |
|---|---|---|
| `GET` list / detail | `list_sitecontactmessage` / `view_sitecontactmessage` | search: name, phone, email, message |
| `PATCH` | `change_sitecontactmessage` | only `status` changes (`new` → `handled` stores `handled_at` / `handled_by`, back to `new` clears them); name, phone, email and message are read only |
| `DELETE`, restore | `delete_…` / `restore_…` | soft delete, as every `TimeModel` |
| `POST` | — | `405`: messages are only created by the public form |

**Multi-tenancy:** a message belongs to an Entity and has no Branch (a visitor does
not choose one, and none is picked for them). `BaseAPIView` therefore scopes it by
`entity_id` only: every Branch of the Entity sees the Entity's messages; another
Entity never does.

The permissions are created by the permission sync like any other model; grant
them to the groups that handle the site's contacts.

## Model

`SiteContactMessage` (`saas/models/site_contact_message.py`, `TimeModel`):
`entity`, `name`, `phone`, `email`, `message`, `site`, `status` (`new` |
`handled`), `handled_at`, `handled_by`. Migration: a new table only (backward
compatible). django_resaas migrations are generated in each install
(`makemigrations django_resaas`).

## Frontend

A site calls the endpoint with `HTTPClient` (no session, no tenant context) — the
browser sets the `Origin`. The Amal clinic site (`dev/front`,
`src/sites/amal/pages/ContactsPage.vue`) is the reference: `s-input` fields, a
hidden `website` input, field errors from `parseFieldErrors`, the error toast from
the API client, `AlertSuccess` on `201`.

## Troubleshooting

| Symptom | Check |
|---|---|
| `404 site_not_found` | `Entity.site` must have the same host (and port) as the page the form is on. A preview URL (`?site=amal` on another host) has a different Origin. |
| `429` | the client address sent more than the rate allows; wait, or raise `RESAAS_SITE_CONTACT_THROTTLE_RATE`. |
| messages stored but nobody is emailed | a notifications rule for `site.contact_message.received` is missing or disabled, or the channel is off (`NotificationSettings`, `NOTIFICATIONS_ENABLED`). |
| staff get `403` on `sitecontactmessages/` | the group lacks `list_sitecontactmessage` / `view_sitecontactmessage`. |

Tests: `saas/tests/test_site_contact.py` (contact form, staff inbox, branches).

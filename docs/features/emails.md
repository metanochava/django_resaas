# Transactional e-mails and their branding

**What.** The e-mails the framework itself sends - verification codes (registration,
contact change, password reset), the password-reset link, the welcome after registration and
the bootstrap welcome - are HTML templates that wear the **look of the Entity or
EntityType** they are about: its name, its logo and its Theme colours.

Code: `saas/core/utils/templates.py` (`render_email_template`),
`saas/core/utils/email_branding.py` (`email_brand`),
`saas/templates/django_resaas/email_*.html`. Business notifications (rules, outbox,
providers) are a different thing: see [Notifications](notifications.md).

## Templates

| Key | Template | Sent by |
|---|---|---|
| `OTP_CODE` | `email_otp.html` | `otp_service.send_registration_otp` (registration, e-mail change, password reset by code) |
| `PASSWORD_RESET` | `email_reset.html` | `password_reset_service.send_link`, legacy `password/reset/email/` |
| `BOOTSTRAP_WELCOME` | `email_welcome.html` | `registration_welcome_service`, `bootstrap_email_service` |

All extend `email_base.html` (header, body, footer). A project replaces one with
`DJANGO_REST_AUTH["EMAIL_TEMPLATES"] = {"OTP_CODE": "my/otp.html"}`; a missing custom
template falls back to the library's.

## Branding

`render_email_template(key, context, request=None, entity=None)`: with a `request` or an
`entity` it fills, **only where the caller left a key empty**, the context of
`email_brand()`:

| Key | Value | Used for |
|---|---|---|
| `entity_name` | Entity name, else EntityType label/name | header text when there is no logo |
| `logo` | Entity logo (unless its LayoutSetting hides the login logo), else EntityType icon | header image |
| `brand_color` | Theme `primary` | header, buttons, the code, the footer rule |
| `brand_text_color` | Theme `header_text` | text on the header and the buttons |
| `brand_tint` | `brand_color` mixed 90% with white | the code box, the footer background |

Which look, first match wins:

1. the `entity` passed explicitly (bootstrap);
2. the Entity whose `site` is the request's Origin (`site_service.entity_for_origin`);
3. the Entity of the authenticated request (`request.entity_id`, from the signed context);
4. the EntityType of the Origin's host: first subdomain label (`www` skipped) equal to
   `EntityType.name`, ignoring case - `saude.example.com` → `Saude` (the frontend's
   `utils/entityTypeHost.js` rule);
5. nothing: the templates' defaults (`#1976d2`, white text, "RESAAS").

An Entity uses its own Theme, else its EntityType's. Without a request or entity (a
terminal command) nothing is resolved.

## Security

- Colours are configurable data that end up inside a `style` attribute: only plain CSS
  colours (`#hex`, `rgb()/rgba()`, `hsl()/hsla()`) are used; anything else is ignored and the
  template default applies.
- The Origin only chooses the look (public data: name, logo, colours); it never chooses who
  receives the message or what link it carries (see
  [Password reset](../security/password-reset.md) for trusted link origins).

## Troubleshooting

| Symptom | Check |
|---|---|
| Default blue header | The Origin matches no `Entity.site` and its first label is no EntityType name, or the Theme `primary` is not a plain CSS colour |
| No logo | The Entity has no logo, or its LayoutSetting has `display_logo_login = False`; for an EntityType, no `icon` |
| A custom template ignores the colours | It must use `brand_color` / `brand_text_color` / `brand_tint` (see `email_base.html`) |

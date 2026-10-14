# Registration (sign-up)

**What.** Public self-registration of a `User`, proving control of an e-mail or phone with a
one-time code. **An account is not access**: registration never creates an `EntityUser`,
`BranchUser`, profile membership (`BranchUserGroup`) or permission. Access to an Entity is
granted afterwards by an authorised operation (e.g. `EntityAPIView.addUser`,
`UserAPIView` with `add_user`, profile assignment through `group_access_service`).

Code: `saas/data/user/views/register_otp.py`, `saas/data/user/views/register.py`,
`saas/data/user/serializers/register.py`, `saas/core/utils/username.py`,
`saas/core/services/otp_service.py`, `saas/data/user/views/registration_throttles.py`.

## Flow

| Step | Endpoint | Access |
|---|---|---|
| 1. Ask for a code | `POST /api/register/otp/request/` `{channel: "email"\|"mobile", identifier}` | PUBLIC (`AllowAny`, in `PUBLIC_BY_DESIGN`), throttled |
| 2. (optional) Check usernames | `GET /api/register/username/?candidates=a,b,c` | PUBLIC, throttled |
| 3. Create the account | `POST /api/register/` `{name?, username, password, channel, identifier, otp}` | PUBLIC, throttled |

Then the user signs in through the normal login (e-mail, mobile or username + password).

### 1. Code request

- The identifier is normalised (e-mail trimmed and lowercased, mobile without spaces).
- **Same answer whether or not the address is already registered**:
  `202 {"sent": true}` with a success alert. No code is sent to a registered address. This
  endpoint never tells who has an account; step 3 says it, after the code proves the
  address is the caller's.
- Errors: `400 invalid_identifier` (bad channel / empty identifier), `503 otp_delivery_failed`
  (the provider failed), `429` (rate limit).

### 2. Username availability

`GET /api/register/username/?candidates=dias.chavana,diaschavana` (up to 8 names, normalised,
duplicates dropped) answers, in the order asked:

```json
{"results": [
  {"username": "dias.chavana", "valid": true, "available": false},
  {"username": "diaschavana", "valid": true, "available": true}
]}
```

Nothing about the account holding a taken name. The answer is only indicative: step 3
checks again and the database `UNIQUE` constraint decides. `400 username_required` without a
name; `429` when rate limited.

### 3. Account creation

Validated in this order, nothing written until all pass:

1. **Username rules** (`saas/core/utils/username.py`): stored lowercase;
   `^[a-z][a-z0-9._]{2,29}$` (3–30 characters, starts with a letter, no `..`/`__`/`._` runs,
   no trailing `.`/`_`). A username can therefore never equal a phone number or an e-mail.
   Unique case-insensitively. A taken name is **refused** (`details.username`), never changed
   into another one.
2. **Attempt limit**: after `OTP_MAX_FAILED_ATTEMPTS` (5) wrong codes for an identifier within
   the 5-minute code window, every attempt fails with `429 too_many_attempts` until it ends.
3. **The code** (TOTP, 6 digits, 5 minutes, derived from the identifier and `OTP_KEY`): a code
   for another address never verifies this one (`details.otp`).
4. **Identifier not registered** (case-insensitive e-mail): `details.identifier`.
5. **Password policy**: Django's `validate_password` with the project's
   `AUTH_PASSWORD_VALIDATORS` (`details.password`).

Then the `User` is saved in one transaction with the e-mail or mobile marked verified,
`first_name`/`last_name` from `name` (first word / the rest), so the auto-created `Person`
gets the name. Concurrent registrations of the same username or identifier: the `UNIQUE`
constraint fails one of them, answered as a clean `400` on the field. `201`:

```json
{"id": "…", "username": "dias.chavana", "email": "dias@example.com", "mobile": null,
 "alerts": [{"level": "success", "message": "Account created successfully"}]}
```

Fields such as `is_staff`, `is_superuser`, `entity_id`, `group_id`, `permissions` in the body
are ignored (the serializer does not declare them).

Errors follow the [error contract](../api/errors-and-alerts.md): validation errors are
`400` with `error.details` = field → messages.

## Rate limits

DRF `SimpleRateThrottle` on Django's cache (same mechanism as the public site's contact form):

| Setting | Scope | Default |
|---|---|---|
| `RESAAS_REGISTER_OTP_THROTTLE_RATE` | code requests per client address | `10/hour` |
| `RESAAS_REGISTER_OTP_IDENTIFIER_THROTTLE_RATE` | codes sent to one e-mail / phone | `5/hour` |
| `RESAAS_REGISTER_THROTTLE_RATE` | registrations per client address | `20/hour` |
| `RESAAS_USERNAME_CHECK_THROTTLE_RATE` | availability checks per client address | `120/hour` |

The counters live in the cache: with several workers, use a shared cache (e.g. Redis) or each
process counts on its own. The test plugin (`django_resaas.testing.pytest_plugin`) clears the
cache around every test.

## Login lookup

`saas/data/user/serializers/login.py` resolves the identifier as: an e-mail
(case-insensitive) when it contains `@`, else a mobile, else a username (case-insensitive) —
one lookup at a time. Old data where a username equals someone else's phone no longer makes
the login ambiguous (it used to raise a 500).

## Creating users as an administrator

`POST /api/django_resaas/users/` (`UserAPIView`) needs `add_user` in the signed context and
links the new user to the current Entity; the Entity context and the capacity (`users`
entitlement) are checked **before** anything is written. Changing another user needs
`change_user` (a user's own personal settings stay self-service); deleting needs
`delete_user`. Superusers keep their own path.

## Not implemented

Invitations and access requests (joining an existing Entity by invitation or by asking)
do not exist; access is granted by an administrator. That is a separate proposal.

## Troubleshooting

| Symptom | Check |
|---|---|
| "a code was sent" but nothing arrives | the address may already be registered (neutral answer by design); the provider (`NOTIFICATIONS_*` / provider credentials) |
| `429` while testing | the rate limits above; clear the cache or raise the settings in the test environment |
| a valid code is refused with `429 too_many_attempts` | 5 wrong codes were tried: wait for the 5-minute window |

Tests: `saas/tests/test_registration_security.py`, `saas/tests/test_register_otp.py`,
`saas/tests/test_user_create_entity.py`.

## See also

- [Password reset (forgot my password)](password-reset.md) - the same OTP service, bound to its own purpose.

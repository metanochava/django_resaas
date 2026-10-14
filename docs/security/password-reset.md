# Password reset ("forgot my password")

**What.** Lets someone without a session choose a new password, proving control of the
account's **e-mail** or **phone number** (`User.email` / `User.mobile`, both unique). They
choose how: a one-time **link**, or a 6-digit **code** (OTP) typed on the page.

Code: `saas/core/services/password_reset_service.py`, `saas/data/user/views/password_reset.py`,
`saas/data/user/serializers/password_reset.py`, `saas/data/user/serializers/set_new_password.py`,
`saas/core/services/otp_service.py`, `saas/data/user/views/registration_throttles.py`.
Frontend: quasar_resaas `pages/auth/ForgotPasswordPage.vue` (`/auth/forgot-password`) and
`pages/auth/ResetPasswordConfirmPage.vue` (`/auth/resetpassword/:uidb64/:token`).

## Flow

| Step | Endpoint | Access |
|---|---|---|
| 1. Send a link or a code | `POST /api/password/reset/request/` `{channel: "email"\|"mobile", identifier, method: "link"\|"otp"}` (`method` defaults to `link`) | PUBLIC (`AllowAny`, `PUBLIC_BY_DESIGN`), throttled |
| 2a. Finish with the code | `POST /api/password/reset/otp/complete/` `{channel, identifier, otp, password}` | PUBLIC, throttled, attempt limit |
| 2b. Finish with the link | the link opens `/#/auth/resetpassword/<uidb64>/<token>`, which sends `PATCH /api/password/reset/complete/` `{uidb64, token, password}` | PUBLIC |

```text
ForgotPasswordPage ── POST password/reset/request/ ─┬─ method=link ─> e-mail / SMS with the link
                                                    │      └─> ResetPasswordConfirmPage ── PATCH password/reset/complete/
                                                    └─ method=otp ──> e-mail / SMS with a code
                                                           └─> ForgotPasswordPage ── POST password/reset/otp/complete/
```

### 1. Request

- The identifier is normalised (e-mail trimmed and lowercased, mobile without spaces) and
  looked up among **active** users.
- **Same answer whether or not the identifier has an account**: `202 {"sent": true,
  "method": …}` with a success alert. Nothing is sent when there is no account. The endpoint
  never tells which e-mails or numbers are registered.
- A link is sent by e-mail (`PASSWORD_RESET` template) or SMS; a code by e-mail
  (`OTP_CODE` template) or SMS, synchronously through the notification providers.
- Errors: `400` (bad `channel`/`method`/empty identifier, in `error.details`),
  `429` (throttle), `503 reset_delivery_failed` (provider failure),
  `503 reset_link_unavailable` (no trusted origin for a link - see Security; checked before
  the account lookup, so it does not reveal anything either).

### 2a. Code

- The code is a TOTP (5 minutes) bound to the identifier **and to the purpose
  `password_reset`** (`otp_service._SCOPED_PURPOSES`): a registration or contact-change
  code never resets a password.
- A wrong code and an unknown identifier give the same `400` with `error.details.otp`.
- After `OTP_MAX_FAILED_ATTEMPTS` (5) wrong codes in the window every attempt, even a right
  code, answers `429 too_many_attempts` (counter per identifier and purpose).
- The new password goes through `AUTH_PASSWORD_VALIDATORS` (`400`, `error.details.password`).
- Success: `202 {"reset": true}`; the password is set and the e-mail / mobile is marked
  verified (receiving the code proved it).

### 2b. Link

- Django's `PasswordResetTokenGenerator`: the token stops working once the password changes
  (single use) or after `PASSWORD_RESET_TIMEOUT`.
- `password/reset/complete/` applies the same password policy (`400`,
  `error.details.password`); the page shows that at the field, and "invalid or expired link"
  only for a bad token.

## Security

Authentication: none (pre-session, PUBLIC on purpose). No tenant context: a User is global.

- **Trusted origin for links.** The link is built on the request's `Origin` only when the CORS
  policy allows it (`CORS_ALLOWED_ORIGINS` or `CORS_ALLOWED_ORIGIN_REGEXES`), else on
  `settings.FRONTEND_URL` / env `FRONTEND_URL`. An Origin outside the policy is never used, so a
  reset cannot be "poisoned" into sending a victim a link to another domain. The legacy
  `POST password/reset/email/` builds its link the same way (it used the raw Origin, on a
  wrong route `/#/resetpassword/…`).
- **No enumeration**: neutral answers in step 1, identical errors in step 2a.
- **Rate limits** (DRF `SimpleRateThrottle` on Django's cache - use a shared cache, e.g. Redis,
  for them to hold across workers):

  | Setting | Applies to | Default |
  |---|---|---|
  | `RESAAS_PASSWORD_RESET_OTP_THROTTLE_RATE` | step 1, per client address | `10/hour` |
  | `RESAAS_PASSWORD_RESET_OTP_IDENTIFIER_THROTTLE_RATE` | step 1, per e-mail / phone | `5/hour` |
  | `RESAAS_PASSWORD_RESET_THROTTLE_RATE` | step 2a, per client address | `20/hour` |

- Existing sessions are **not** ended by a reset (same as before). See Future work.

## Legacy endpoints (kept for compatibility)

| Endpoint | Status |
|---|---|
| `POST password/reset/email/` `{email}` | Still works (link by e-mail, now on a trusted origin). New clients use `password/reset/request/`. |
| `GET password/reset/<uidb64>/<token>/` | Unchanged (redirect check). |
| `POST password/change/mobile/` `{mobile, otp, password}` | **Deprecated**: counter-based HOTP, no attempt limit, no password policy, legacy `alert_*` bodies. Not used by quasar_resaas' forgot-password page any more. Remove once no client calls it. |

## Troubleshooting

| Symptom | Check |
|---|---|
| `503 reset_link_unavailable` | The page's origin is not in `CORS_ALLOWED_ORIGINS` / `CORS_ALLOWED_ORIGIN_REGEXES` and `FRONTEND_URL` is unset. Add the origin to the CORS policy (do not loosen it to "allow all"), or ask for a code |
| `503 reset_delivery_failed` | No e-mail / SMS provider configured or the provider failed (see notifications providers) |
| The code is always "invalid" | Clock skew on the server (TOTP), the code is older than 5 minutes, or it was a registration code |
| `429` | Throttle or attempt limit; wait for the window |

## Future work

- End the user's other sessions after a reset (`session_service`).
- Remove `password/change/mobile/` once unused.

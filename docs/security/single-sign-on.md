# Single sign-on between domains

**What.** One deployment serves many frontend domains (one per EntityType site,
for example `docodela.co.mz`, `saas.mytech.co.mz`). The account (`User`) is the
same on all of them, but a session lives in each domain's own browser storage.
Single sign-on lets a session on one domain start a **new session** on another
without typing the password again.

Code: `saas/core/services/sso_service.py`, `saas/data/user/views/sso.py`,
`saas/models/sso_authorization_code.py` (migration `0010_sso_authorization_code`),
`saas/data/user/views/registration_throttles.py` (`SsoTokenThrottle`).
Tests: `saas/tests/test_sso.py`.
Frontend: quasar_resaas `services/sso.js`, `pages/auth/SsoPage.vue`, `router/authGuard.js`,
`components/FormLogin.vue` (see its routing docs).

## Model

An authorization code with PKCE (RFC 7636, S256 only), reduced to what RESAAS
needs. One domain is **central** (the frontend's `SSO_URL`, for example
`https://auth.mytech.co.mz`); the others are **clients**.

| Endpoint | Access | Body / query | Answer |
|---|---|---|---|
| `POST /api/sso/code/` | PROTECTED (`IsAuthenticated`) | `{redirect_uri, code_challenge}` | `{code, expires_in}` |
| `POST /api/sso/token/` | PUBLIC (`PUBLIC_BY_DESIGN`), throttled | `{code, code_verifier, redirect_uri}` | the same body as `POST /api/login/` (`id`, `email`, `username`, `mobile`, `tokens`, ...) |
| `GET /api/sso/redirect_check/?redirect_uri=` | PUBLIC (`PUBLIC_BY_DESIGN`), throttled, read-only | `redirect_uri` | `{allowed: true}` |

## Rules

- **Only from a full session.** `sso/code/` needs an access token. Tokens exist only
  after the password step, two-factor and a temporary-password change, so a code
  never skips them.
- **Trusted destinations only.** `redirect_uri` must be a plain `http(s)` URL (no
  credentials, at most 500 characters) whose origin the CORS policy trusts:
  `CORS_ALLOWED_ORIGINS` or `CORS_ALLOWED_ORIGIN_REGEXES` (the frontends that may call
  this API). With `CORS_ORIGIN_ALLOW_ALL = True` no destination is trusted.
  Otherwise: 400 `sso_invalid_redirect`.
- **Single use, short life.** A code lives `CODE_TTL` (60) seconds. Only a keyed hash
  (`salted_hmac`) is stored. Redeeming locks the row (`select_for_update()`) and marks
  it used on the first presentation, even when the rest of the check fails.
- **Bound.** The redeemed code must come with the same `redirect_uri` and a
  `code_verifier` whose S256 hash is the stored `code_challenge`
  (`code_challenge`: 43 base64url characters; verifier: 43–128 unreserved characters).
- **Live source.** The code dies when the user is deactivated or the session it was
  issued from (its refresh token `jti`) has been ended (blacklisted).
- **Same answer for every failure.** Unknown, used, expired, wrong verifier, wrong
  `redirect_uri`, inactive user, ended source session or a malformed body all answer
  401 `sso_code_invalid`.
- **A new session.** Redeeming mints a new refresh token and a `UserLogin` row
  (`session_service.record_login`), so the session appears in `GET /api/sessions/`
  and can be ended like any other. The event is audited as `SSO_SIGN_IN` (details:
  the destination origin).
- **No tenant context.** Entity, Branch and Group are not carried: each domain
  chooses and validates its own (`X-RESAAS-Context`).

Expired codes of a user are deleted when that user is issued a new one.

## Settings

| Setting | Default | Use |
|---|---|---|
| `CORS_ALLOWED_ORIGINS`, `CORS_ALLOWED_ORIGIN_REGEXES` | — | the trusted destinations; the central domain must be in them too |
| `RESAAS_SSO_TOKEN_THROTTLE_RATE` | `60/hour` | per client address, for `sso/token/` and `sso/redirect_check/` |

The throttle counts in Django's cache; it holds across workers only with a shared
cache (e.g. Redis).

## Errors

| Code | Status | When |
|---|---|---|
| `sso_invalid_redirect` | 400 | `redirect_uri` is not a trusted destination |
| `sso_invalid_request` | 400 | `code_challenge` is missing or malformed |
| `sso_code_invalid` | 401 | the code cannot be redeemed (any reason) |

Messages are translated (`saas/lang/ptpt.py`).

## Limits

- Signing out on one domain ends that domain's session only. To end every session,
  use the account's sessions list (`POST /api/sessions/terminate_others/` or
  `POST /api/sessions/<jti>/terminate/`). An access token already issued lives out its
  few minutes.
- The concurrency test (two simultaneous redemptions) needs a server database; it is
  skipped on SQLite.

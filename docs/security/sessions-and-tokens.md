# Sessions and tokens

**What.** The API authenticates with **JWT only** (`Authorization: Bearer
<access>`). A sign-in mints a refresh token. The refresh token **rotates**:
every refresh answers a new one and blacklists the one used. A sign-in is a
**session**, with a stable id, that the user can list and end (2026-11-13).

Code:

- `saas/core/services/session_service.py`
- `saas/data/user/views/login.py`: `TokenRefreshView`, `RotatingTokenRefreshSerializer`
- `saas/models/user_login.py`: `token_jti`, `current_jti`; migration `0021_userlogin_current_jti`
- the application's `SIMPLE_JWT` settings
- frontend: quasar_resaas `stores/UserStore.js` (`refreshToken`)

Tests:

- `saas/tests/test_refresh_rotation.py`
- `test_authentication_jwt_only.py`
- the session, single sign-on, logout and two-factor tests

## Authentication

`REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` is `JWTAuthentication` only:

- **Basic** sent a password on any request, past the login throttle and
  two-factor; it is refused even with the right password.
- **Token** was unused: no tokens were issued.
- **Session** let a Django admin cookie authenticate the API.

## Settings

| Setting | Value | Use |
|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | minutes (dev: 4) | how long an access token works |
| `REFRESH_TOKEN_LIFETIME` | 1 day | how long a refresh token works; it is renewed on each refresh, so an active session keeps going |
| `ROTATE_REFRESH_TOKENS` | `True` | each refresh answers a new refresh token |
| `BLACKLIST_AFTER_ROTATION` | `True` | the refresh token used is blacklisted |

## Sessions

- **The session's id** is the jti of the sign-in's first refresh token.
  - It is kept in `UserLogin.token_jti` and in the tokens' `sid` claim.
  - simplejwt keeps custom claims on rotation, so the id never changes.
  - The session list, "end this session", the single sign-on family and
    `sso/code/` all use it.
- **The current token** is `UserLogin.current_jti`. A refresh moves it to the
  new token (`session_service.rotated`). Sessions from before rotation have it
  null: their current token is `token_jti`.
- **Active:** the current token is outstanding, not blacklisted and not
  expired.
- **Ended:** the current token is blacklisted (`terminate`,
  `terminate_others`, `terminate_sso_family`, logout). A rotation blacklists the
  previous token, never the current one, so a rotated session is not "ended".

## A rotated token used again

A refresh that is refused goes through `session_service.refresh_reused`:

- **Taken as stolen:** a genuine token, the session's previous one,
  blacklisted more than `REUSE_GRACE_SECONDS` (60) ago, means someone else
  holds a copy.
  - The session and its whole single sign-on family end.
  - The event is audited as `SESSION_TOKEN_REUSED` (details: the session,
    how many sessions ended).
- **Only refused:** within the 60 seconds it is two tabs (or a retry)
  refreshing at once.
- **Plain refusal:** a forged, expired or unknown token, or the session's
  current token that was ended.

## The refresh token in an HttpOnly cookie (phase 2)

`core/services/refresh_cookie.py` covers the frontends of the API's own site.
The setting `RESAAS_REFRESH_COOKIE_SITES` lists those sites; dev uses
`["mytech.co.mz"]`, so `venda.dev.mytech.co.mz` → `app.dev.mytech.co.mz`.

- **Where the token goes.** An answer that carries a refresh token sets it in
  the cookie instead and drops it from the body. The body gets
  `refresh_cookie.expires_at`. `ResaasResponseMixin` does this for every token
  answer: login, two-factor, the temporary password change, single sign-on,
  registration and refresh.
- **The cookie.** `resaas_refresh`, `HttpOnly`, `Secure`, `SameSite=Lax`,
  `Path=/api/` (`RESAAS_REFRESH_COOKIE_PATH`), max age = the refresh lifetime.
- **Reading it.**
  - `refresh_token/`, `logout/` and `sso/token/` (`previous_refresh`) read the
    cookie when the body has none.
  - It is read only when the request's `Origin` is a cookie site. This is the
    CSRF guard, on top of `SameSite=Lax`.
- **Clearing it.** `logout/` and `sso/logout/` clear the cookie.
- **Own domains** (e.g. `clinicaamal.co.mz`) keep the refresh token in the
  body. There the cookie would be a third-party one, which browsers block.
- **CORS.** `CORS_ALLOW_CREDENTIALS = True`. The allowed origins are an
  explicit list or regex, never `*`.

Tests: `saas/tests/test_refresh_cookie.py`.

## The API under an own domain (phase 3)

A site on its own domain (e.g. `clinicaamal.co.mz`) gets a first-party
cookie by talking to its OWN origin: its web server proxies the API there.

- **nginx**, in the site's `server` block:
  ```nginx
  location /api/   { include proxy_params; proxy_pass http://127.0.0.1:<backend port>; }
  location /media/ { alias <backend>/mediafiles/; }
  ```
- **Backend:**
  - the domain is in `ALLOWED_HOSTS`;
  - it is in `RESAAS_REFRESH_COOKIE_SITES`, so the cookie is used there.
- **Frontend:**
  - the domain is in `API_SAME_ORIGIN_HOSTS` (the front's `.env`, passed by
    `quasar.config.js`);
  - quasar_resaas `services/apiOrigin.js` then uses the page's origin instead
    of `process.env.API`, both for the API (`services/api.js`) and for file
    URLs (`services/app.js` `urlBase`).
- **Unchanged:** the Origin → Entity resolution of public endpoints (the
  Origin is the same domain).

Rehearsed in dev on `amal.dev.mytech.co.mz` (2026-11-14):
`API_SAME_ORIGIN_HOSTS=amal.dev.mytech.co.mz`, the nginx locations above, and
`ALLOWED_HOSTS`.

## Frontend

- **The access token lives in memory only** (`UserStore.access`), never in
  storage. A script that reads the storage finds none, and one left by an
  older version is dropped on load.
- **After a reload,** `services/api.js` mints an access token from the
  refresh token before the first request.
- **The session check** is `services/sessionToken.js`: an access token in
  memory, or a stored refresh token that has not expired (`hasSessionToken`,
  `liveRefreshToken`). The route guard and `UserStore.hasSession` use it.
- **The refresh token.** On the API's own site it is in the HttpOnly cookie:
  the store keeps only `refreshUntil`, when the cookie expires. On other sites
  it is in localStorage.
- **The session check** also counts the cookie (`cookieSessionLive`,
  `canRefresh`).
- **The HTTP clients** send the cookie (`withCredentials: true`).
- **Two tabs at once on the cookie.** The tab that loses retries once; the
  browser already holds the cookie the other tab rotated.

`UserStore.refreshToken` stores the new refresh token from every refresh.
The tabs of a browser share it in localStorage:

- a tab uses the token another tab already rotated;
- when a tab loses a race to another tab, it retries once with the stored
  token.

`services/api.js` refreshes through it on a 401 (one refresh at a time per
tab).

## Next

- **Phase 3 in pro:** `clinicaamal.co.mz` and `docodela.co.mz` (nginx, settings, front `.env`, release).
- **Sign-in without leaving the page:**
  - a hidden iframe to the central domain for `*.mytech.co.mz`;
  - a popup for the own domains.

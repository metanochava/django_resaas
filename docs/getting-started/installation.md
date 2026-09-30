# Installation

`django_resaas` is a reusable Django app: it plugs into a normal Django project rather than
running as one. This page wires it up from a blank project to a server that answers real API
requests. Every snippet below matches the framework's own runnable example project,
[`src/dev/`](../../src/dev/README.md) (`settings.py`, `urls.py`), which the test suite runs — when
in doubt, copy from there.

## 1. Install

`django_resaas` is published on PyPI (Python 3.9+; it pins Django 5.2 and DRF 3.16):

```bash
python -m venv venv && source venv/bin/activate
pip install django_resaas
django-admin startproject myproject
```

## 2. `settings.py`

```python
from datetime import timedelta
from corsheaders.defaults import default_headers

AUTH_USER_MODEL = 'django_resaas.User'

MY_APPS = [
    'django_resaas.saas',            # the core: tenants, users, groups, schema, CRUD engine
    'django_resaas.notifications',   # email / SMS / WhatsApp outbox
    'your_app',                      # your own app(s) / modules
]

# modules activated for every new EntityType, besides the framework's own
# (optional; default [] - e.g. ["your_app"])
RESAAS_DEFAULT_MODULES = []

INSTALLED_APPS = MY_APPS + [
    'djmoney',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'django_filters',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_resaas.saas.core.middleware.file_access.FileAccessMiddleware',
    'django_resaas.saas.core.middleware.tenant.TenantContextMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    # empty on purpose: views declare their own access (BaseAPIView is protected by
    # default; anything public says so explicitly) - see security/permissions.md
    'DEFAULT_PERMISSION_CLASSES': (),
    # every error answers {"error": {code?, message, details}} - see api/errors-and-alerts
    'EXCEPTION_HANDLER': 'django_resaas.saas.core.exceptions.handler.resaas_exception_handler',
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# The frontend (quasar_resaas) runs on another origin and sends its own headers on every
# request: L (language), X-RESAAS-Context (signed tenant context), FEK/FEP (frontend keys).
# Without them in CORS_ALLOW_HEADERS the browser blocks every call.
CORS_ALLOWED_ORIGINS = ['http://localhost:9000']          # your frontend's origin(s)
CORS_ALLOW_HEADERS = list(default_headers) + ['FEK', 'FEP', 'L', 'x-resaas-context']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

`TenantContextMiddleware` resolves the tenant (Entity / Branch / Group) of every request from its
signed `X-RESAAS-Context` header; `FileAccessMiddleware` protects uploaded files. A third one,
`FrontEndMiddleware` (`django_resaas.saas.core.middleware.front_end.FrontEndMiddleware`), is
optional: add it to require the `FEK`/`FEP` frontend credentials — see
[Middleware](../architecture/middleware.md).

Email, notifications (`NOTIFICATIONS_ENABLED`, the outbox settings) and Celery are optional and
off by default; `src/dev/settings.py` lists every setting with its environment variable, and
[Notifications](../features/notifications.md) explains when you need them.

## 3. `urls.py`

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from django_resaas.saas.core.utils.autoload_urls import build_saas_urls

urlpatterns = [
    path('api/', include('django_resaas.urls')),
    path('api/your_app/', include('your_app.urls')),   # only if your app has hand-written URLs
    path('admin/', admin.site.urls),
]

# every @registerView class becomes a route: /api/<module>/<name>/
router, extra_patterns = build_saas_urls()
urlpatterns += [path('api/', include(router.urls))]
urlpatterns += extra_patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

`build_saas_urls()` walks `VIEW_REGISTRY`; call it after the `include()`s above so every
`@registerView` class has been imported — see
[View registry](../architecture/registry.md#when-view_registry-is-actually-populated).

## 4. Migrate and bootstrap

```bash
python manage.py migrate
python manage.py resaas_setup    # languages, frontend defaults, translations (safe to repeat)
python manage.py create_entity   # interactive: superuser + first tenant (Entity/Branch) + Admin group
python manage.py migrate         # again - see below
```

> [!WARNING]
> The second `migrate` is not a typo. CRUD permissions (`list_<model>`, `add_<model>`, ...)
> are created by a `post_migrate` signal that no-ops until at least one `EntityType` exists —
> `create_entity` is what creates the first one. Re-running `migrate` (idempotent — it
> applies no new migrations) fires that signal again now that the guard condition is met.
> Skip this step and every request will fail authorization with no permissions available to
> grant to any group.

`create_root` is the non-interactive alternative for a brand-new environment (superuser + full
default tenant structure in one command); `create_entity` also adds another entity/branch under
an existing setup. `resaas_doctor` checks an installation. All are covered in
[Management commands](../development/management-commands.md).

## 5. Run it

```bash
python manage.py runserver 0.0.0.0:7002
```

`GET http://localhost:7002/api/django_resaas/languages/` should answer with the languages
`resaas_setup` loaded. From here, continue to [Quick start](quick-start.md) to register your
first model end to end, or go straight to [Creating a new resource](../development/creating-resource.md).

## Frontend half

This page only covers the backend. The companion frontend package, `quasar_resaas` (Vue 3 +
Quasar), has its own installation guide — `docs/quasar-resaas/getting-started/installation.md`
in that repository (the documentation site shows both).

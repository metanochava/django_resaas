# Installation

`django_resaas` is a reusable Django app: it plugs into a normal Django project rather than
running as one. This page wires it up from a blank project to a server that answers real API
requests. For the fully worked, runnable version of everything below — real model, real `curl`
calls — see [`src/dev/README.md`](../../src/dev/README.md), the project's own example app.

## 1. Install

```bash
pip install django_resaas
```

## 2. `settings.py`

```python
AUTH_USER_MODEL = 'django_resaas.User'

MY_APPS = [
    'django_resaas',
    'hr',                   # the framework's own bundled module - see modules/hr-overview.md
    'your_app',              # your own app(s)
]

INSTALLED_APPS = MY_APPS + [
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
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    # ... Django's defaults ...
    'django_resaas.core.middleware.file_access.FileAccessMiddleware',
    'django_resaas.core.middleware.tenant.TenantContextMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PERMISSION_CLASSES': (),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}
```

`hr` is not optional in practice: `django_resaas/urls.py` unconditionally includes `hr.urls`, so
any project installing `django_resaas` needs `hr` installed too — see
[`modules/hr-overview.md`](../modules/hr-overview.md).

`TenantContextMiddleware` and `FileAccessMiddleware` are the two middleware classes enabled by
default — see [`architecture/middleware.md`](../architecture/middleware.md) for what each one
does and for the third one (`FrontEndMiddleware`) that ships but isn't wired in by default.

## 3. `urls.py`

```python
from django.urls import path, include
from django_resaas.core.utils.autoload_urls import build_saas_urls

urlpatterns = [
    path('api/', include('django_resaas.urls')),
    path('api/your_app/', include('your_app.urls')),
]

# MUST run after the include()s above - see architecture/registry.md#when-view_registry-is-actually-populated
router, extra_patterns = build_saas_urls()
urlpatterns += [path('api/', include(router.urls))]
urlpatterns += extra_patterns
```

`build_saas_urls()` walks `VIEW_REGISTRY`, which is only populated once every `@register_view`
class has actually been imported — which happens as a side effect of the `include()` calls above
running first. Ordering matters here; see
[`architecture/registry.md`](../architecture/registry.md#when-view_registry-is-actually-populated)
for why.

## 4. Migrate and bootstrap

```bash
python manage.py migrate
python manage.py create_entity   # interactive: superuser + tenant + Admin group
python manage.py migrate         # again - see below
```

The second `migrate` is not a typo. CRUD permissions (`list_<model>`, `add_<model>`, ...) are
created by a `post_migrate` signal that no-ops until at least one `EntityType` exists —
`create_entity` is what creates the first one. Re-running `migrate` (idempotent — it applies no
new migrations) fires that signal again now that the guard condition is met. Skip this step and
every request will fail authorization with no permissions available to grant to any group.

`create_root` is the alternative, non-interactive-friendlier bootstrap for a brand-new
environment (superuser + full default tenant structure in one command); `create_entity` is for
adding another entity/branch under an existing setup. Both are covered in
[`development/management-commands.md`](../development/management-commands.md).

## 5. Run it

```bash
python manage.py runserver 0.0.0.0:7002
```

From here, continue to [Quick start](quick-start.md) to register your first model end to end, or
jump straight to [Creating a new resource](../development/creating-resource.md) for the reference
walkthrough.

## Frontend half

This page only covers the backend. The companion frontend package, `quasar_resaas` (Vue 3 +
Quasar), has its own installation guide in its own docs — switch product to `quasar_resaas` at
the top of the sidebar if you're reading this from the self-hosted docs viewer, or see that
package's own `docs/quasar-resaas/getting-started/installation.md` in its repo.

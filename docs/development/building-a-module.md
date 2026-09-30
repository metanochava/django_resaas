# Building a module

A **module** is a Django app of your application built on `django_resaas`:
Health, Sales, HR, ... The framework provides the mechanisms, and the module
provides the domain. The framework never names a business module. It starts,
migrates and passes its tests with none installed.

A real example is an application's `hr` module (employees, contracts, payroll).
It used to ship inside `django_resaas`, and now lives in the application that
uses it, as described below.

## The pieces

| What | How | Where |
|---|---|---|
| Models | `BaseModel` (tenant fields, soft delete, audit) | `<module>/models/` |
| API | `BaseSerializer` + `BaseAPIView`, registered with `@register_view("<resource>", module="<label>")` | `<module>/views/` |
| Routes | none to write: `build_saas_urls()` serves every registered view at `/api/<label>/<resource>/` | — |
| Load the views at startup | import them in `AppConfig.ready()`, so their decorators (and `@resaas_action`) run before `post_migrate` | `<module>/apps.py` |
| Activation per tenant | `App` + `EntityApp` (a module is active per Entity). New EntityTypes get the framework's own apps plus `settings.RESAAS_DEFAULT_MODULES` | settings |
| Profiles (Group templates) | `group_creator(PROFILES)` from a `post_migrate` receiver. It is additive by profile name, so a module can add its permissions to profiles defined elsewhere (e.g. the platform's "Organization Administrator") | `<module>/profiles.py` |
| Module permissions that are not model CRUD | `ensure_module_permissions("<label>", [{"codename", "name"}, ...])` from a `post_migrate` receiver | `<module>/apps.py` |
| Dashboards | `DASHBOARD` / `DASHBOARDS` in `<module>/dashboard.py`, autodiscovered | [Dashboards](../architecture/dashboards.md) |
| Translations | `<module>/lang/<code>.py` (`key_value` dict), merged by `Translate.tdc` | [Translation](https://github.com/metanochava/quasar_resaas/blob/main/docs/quasar-resaas/features/translation.md) |

### `apps.py` of a module

```python
import importlib
import pkgutil

from django.apps import AppConfig
from django.db.models.signals import post_migrate

MODULE_PERMISSIONS = [{"codename": "view_sales_dashboard", "name": "Can view Sales dashboard"}]


def create_sales_permissions(sender, **kwargs):
    if kwargs.get("app_config").label != "sales":
        return
    from django_resaas.saas.core.signals.permissions import ensure_module_permissions
    ensure_module_permissions("sales", MODULE_PERMISSIONS)


def create_sales_profiles(sender, **kwargs):
    if kwargs.get("app_config").label != "sales":
        return
    from django_resaas.saas.models.entity_type import EntityType
    if not EntityType.objects.exists():
        return
    from django_resaas.saas.core.utils.group_creator import group_creator
    from sales.profiles import SALES_PROFILES
    group_creator(SALES_PROFILES)


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sales"

    def ready(self):
        import sales.views
        for _, name, _ in pkgutil.iter_modules(sales.views.__path__):
            importlib.import_module(f"sales.views.{name}")

        # permissions first: the profiles grant some of them
        post_migrate.connect(create_sales_permissions, sender=self)
        post_migrate.connect(create_sales_profiles, sender=self)
```

### Settings of the application

```python
MY_APPS = [
    "django_resaas.saas",
    "django_resaas.notifications",
    "sales",
]

# activated for every new EntityType, besides the framework's own apps
RESAAS_DEFAULT_MODULES = ["sales"]
```

## Security

A module adds no security layer of its own. Its views inherit
`BaseAPIView`'s chain: authentication, tenant context, whether the module is
active for the Entity, action permission, and object scope. See
[Permissions](../security/permissions.md) and
[Multi-tenancy](../architecture/multi-tenancy.md). Activation (`EntityApp`)
and permissions are separate: both must pass.

## Testing a module

The framework's tenant fixtures are public (`django_resaas.testing`):

```python
# conftest.py of the application
pytest_plugins = ["django_resaas.testing.pytest_plugin"]
```

```python
def test_invoices_are_listed(bootstrap_tenant):
    tenant = bootstrap_tenant("alice", modules=("sales",))

    response = tenant["client"].get("/api/sales/invoices/")

    assert response.status_code == 200
```

`bootstrap_tenant(username, modules=())` creates an Entity, a Branch, a user in
the Root group, and a signed tenant context. It returns `user`, `entity`,
`branch`, `root_group`, `context` and `client` (an authenticated `APIClient`).
`activate_module(entity, name)` activates one more module. Both also work
without pytest: `from django_resaas.testing import bootstrap_tenant`.

## Migrations

A module's migrations are its own. The framework ships its own
(`django_resaas`, `notifications`), and a module depends on them by their
shipped names, e.g. `("django_resaas", "0001_initial")`. See
[Upgrading](../deployment/upgrading.md).

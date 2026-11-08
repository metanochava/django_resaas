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
| Profiles (Group templates) | `group_creator(PROFILES)` from a `post_migrate` receiver. It is additive by profile name, so a module can add its permissions to profiles defined elsewhere (e.g. the platform's "Admin"). Each profile is linked to the `SaaS` EntityType (`EntityTypeGroup`) and to the platform Entity - the oldest Entity of that type (`EntityGroup`); before `create_root` created it there is no platform Entity and only the type link is made (no Entity is created) | `<module>/profiles.py` |
| Module permissions that are not model CRUD | `ensure_module_permissions("<label>", [{"codename", "name"}, ...])` from a `post_migrate` receiver | `<module>/apps.py` |
| Dashboards | `DASHBOARD` / `DASHBOARDS` in `<module>/dashboard.py`, autodiscovered | [Dashboards](../architecture/dashboards.md) |
| Translations | `<module>/lang/<code>.py` (`key_value` dict), merged by `Translate.tdc` | [Translation](https://github.com/metanochava/quasar_resaas/blob/main/docs/quasar-resaas/features/translation.md) |

### One class per file

Models, views and serializers are packages - `<module>/models/`, `<module>/views/`,
`<module>/serializers/` - with **one class per file**, named after the class in
snake_case without its suffix (`JournalEntryLine` → `models/journal_entry_line.py`,
`JournalEntryLineAPIView` → `views/journal_entry_line.py`, `JournalEntryLineSerializer` →
`serializers/journal_entry_line.py`). This includes `TextChoices` enums
(`hr/models/leave_request_status.py`) and throttles. The package `__init__.py` re-exports
the classes, so `from <module>.models import X` keeps working; module-level constants that
belong to a model (e.g. `ALLOWED_TRANSITIONS`) live in that model's file, and helpers shared
by several classes of a package live in its `_common.py`. `saude` is the reference layout.

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

### Keeping the suite fast

- Every `bootstrap_tenant` creates a user: with Django's production hasher
  (PBKDF2) hashing dominates. Use a fast hasher in the tests only, e.g. in the
  application's `conftest.py`:

  ```python
  def pytest_configure(config):
      from django.conf import settings
      settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
  ```

- `pytest --nomigrations` builds the test tables from the models. Creating the
  test database through every migration can take minutes in an application with
  many modules; check the migrations separately (`makemigrations --check` and a
  `migrate` on an empty database), and keep a data migration's behaviour covered
  by its own test if a test depends on it.

## Migrations

A module's migrations are its own. The framework ships its own
(`django_resaas`, `notifications`), and a module depends on them by their
shipped names, e.g. `("django_resaas", "0001_initial")`. See
[Upgrading](../deployment/upgrading.md).

## Sidebar menu (`<app>/sidebar.py`)

`GET /api/django_resaas/users/<id>/menus/` (`UserAPIView.menus`) reads `ALL`
from the `sidebar.py` of every module that is active and entitled for the
Entity type. It keeps only what the selected profile (BranchUserGroup) may
see. Each entry of `ALL` is one of:

- **a group:** `{"MENU", "ICON", "SUBMENUS": [...]}`. Each submenu item has
  `menu`, `icon`, `route` and `role`, plus optional `add_route` / `add_role`
  (the **+** button) and a nested `submenu`. An item is kept when its `role`
  is among the profile's permissions; a group with no item left is dropped.
- **a direct link:** `{"MENU", "ICON", "ROUTE", "ROLE"}`, with no `SUBMENUS`.
  It is shown only when the profile has `ROLE`; a link without `ROLE` is
  never shown (fail closed). The API returns it as
  `{"menu", "icon", "route", "submenu": []}`. quasar_resaas
  (`LeftMenuSegundo`, `TopMenuSegundo`, `isMenuLink()` in
  `services/routing.js`) opens the route in one click instead of a submenu.
  Example: saude's top-level "Patients" → `list_paciente`, which stays inside
  the Saude group too.

**Hiding a module per profile:** a profile (Group) can hide a module from its
menu without changing its permissions (`Group.hidden_menu_apps`, app labels).
The Permissions modal (quasar_resaas `PermissionManager`, eye button on each
module) calls `POST /api/auth/groups/{id}/menu_visibility/`
`{"app_label": "saude", "visible": false}`. That call is PROTECTED: it needs
`change_group` and follows the same "group changeable" rules as
`setGroupPermissions`. An unknown module or a non-boolean `visible` is a 400.
`menus` skips the menu groups (`SUBMENUS`) of a hidden module. Its direct
links do not depend on the module's visibility: they follow only their own
permission (below), so a profile can hide the Saude group and keep the
top-level "Patients" link. `GroupSerializer` returns
`hidden_menu_apps`, and `PermissionSerializer` returns each permission's
`app_label`.

**Hiding one permission's menu entries per profile:** the same call with
`{"permission": "list_paciente", "visible": false}` hides every menu entry
whose `ROLE` / `role` is that codename, and the **+** button whose `add_role`
is that codename (`Group.hidden_menu_permissions`, lowercase codenames). The
permission stays granted: the profile can still open the route. Only codenames
that some `sidebar.py` uses can be hidden (`saas/core/menus.py`
`menu_roles()`); any other codename is a 400 `unknown_menu_permission`.
`GroupSerializer` returns `hidden_menu_permissions` and `menu_permissions`
(the codenames the sidebars use, the same list for every group). The
Permissions modal shows an eye button next to each of these permissions.
`menus` builds the menu from the profile's permissions minus the hidden ones.

Tests: `saas/tests/test_menus_direct_link.py`, `saas/tests/test_menus_superuser.py`,
`saas/tests/test_menu_visibility.py`.

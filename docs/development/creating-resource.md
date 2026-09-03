# Creating a New Backend Resource

The full checklist for adding one resource (model → API → schema) to an app already installed
alongside `django_resaas`. For the very first resource in a brand-new project, do
[Installation](../getting-started/installation.md) first — this page assumes `urls.py` is already
wired up and at least one `EntityType` exists.

## 1. Model

Inherit `BaseModel` for anything tenant-scoped (gets `entity`/`branch`, soft delete,
`created_by`/`updated_by` for free — see [Multi-tenancy](../architecture/multi-tenancy.md)), or
`TimeModel`/`SoftBaseModel` for something global with no tenant (the framework's own `User`,
`Entity`, etc. are built this way).

```python
# your_app/models/patient.py
from django.db import models
from django_resaas.core.base.models import BaseModel

class Patient(BaseModel):
    nid = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)

    class RESAAS:
        label_field = "name"
        search_fields = ["nid", "name"]
        crud = True
```

```bash
python manage.py makemigrations your_app
python manage.py migrate
```

See [Models & RESAAS](../models/resaas-config.md) for every `class RESAAS` attribute.

## 2. Serializer

Inherit `BaseSerializer` rather than DRF's `ModelSerializer` directly — it already marks
`id`/`entity`/`branch`/`created_by`/`updated_by`/`created_at`/`updated_at`/`deleted_at` read-only,
and brings dynamic-fields, file-field (see [Files and PDF](../features/files-pdf.md)) and
label/value representation used across the framework:

```python
# your_app/serializers/patient.py
from django_resaas.core.base.serializers import BaseSerializer
from your_app.models.patient import Patient

class PatientSerializer(BaseSerializer):
    class Meta:
        model = Patient
        fields = "__all__"
```

Full mixin breakdown in [Public API reference](../api/public-api-reference.md#baseserializer---django_resaascorebaseserializersbaseserializer).

## 3. View

Inherit `BaseAPIView`, not a plain DRF `ModelViewSet`, unless the resource genuinely needs none of
tenant scoping, permissions or module activation:

```python
# your_app/views/patient.py
from django_resaas.core.base.views import BaseAPIView, register_view
from your_app.models.patient import Patient
from your_app.serializers.patient import PatientSerializer

@register_view("patients", module="your_app")
class PatientAPIView(BaseAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
```

`register_view` is the same decorator under a PEP 8-consistent name (`registerView =
register_view`) — use whichever you like, both stay supported; every existing call site in
`hr/views/*.py` uses `registerView`. `name` (the URL prefix segment) defaults to the class name
lowercased with `APIView` stripped and an `s` appended if omitted; `module` defaults to the
class's top-level package. See [View registry](../architecture/registry.md) for exactly what the
decorator does.

That's already full CRUD, pagination, ordering, `?search=`, soft delete/restore/hard delete, and a
schema endpoint — nothing else to write for the base behavior.

### Custom actions (`@resaas_action`)

```python
@registerView("sales")
class SaleAPIView(BaseAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer

    @resaas_action(
        methods=["post"],
        detail=True,
        label="Confirm",
        permission="confirm_sale",  # optional - see below
    )
    def confirm(self, request, pk=None):
        ...
```

The decorator only attaches metadata to the method; `ActionSyncService` (run from `post_migrate`
and `manage.py sync_actions`) is what actually creates/updates the `ModelExtraAction` row and the
Django `Permission`.

- **Permission ownership**: if `permission=` is omitted, the codename defaults to
  `f"{action_name}_{model_name}"`. Passing `permission=` explicitly lets an action reuse a
  permission that already exists on the same model (e.g. two actions sharing one "can manage"
  gate) — the lookup is always scoped to the model's own `ContentType`, so a same-named permission
  on an unrelated model is never reused by mistake, and a shared/explicit permission's `.name` is
  never auto-rewritten (unlike the default-convention case, where it IS kept in sync with the
  action's label/model as long as the permission is RESAAS-managed).
- **Manual vs. decorator**: a `ModelExtraAction` row with `managed_by="manual"` (the default for
  anything created outside `ActionSyncService`, e.g. by hand via the admin) can never be silently
  taken over by a decorator of the same `app.model.action` — syncing raises
  `ImproperlyConfigured` instead. To hand an action over to the decorator on purpose, set
  `managed_by="decorator"` on the existing row yourself first.
- **Multiple views, one model**: two different views can each declare actions for the same model
  without stepping on each other — orphan removal only happens in `sync_registry()` (the
  `post_migrate`/`sync_actions` entry point), which aggregates every registered view's actions
  before deciding what no longer exists. Calling `sync_view()` directly on a single view only
  upserts; it never deletes.

Full argument reference and permission ownership rules in
[Permissions](../security/permissions.md#custom-action-permissions-and-ownership).

## 4. Routes

Nothing to register manually. `build_saas_urls()` (`urls.py`) walks `VIEW_REGISTRY` and registers
every `@register_view`'d class on a `DefaultRouter` automatically — the only requirement is that
the module defining the view actually gets *imported* before `build_saas_urls()` runs (typically
via the app's own `views/__init__.py`, imported as a side effect of `include()`-ing the app's
`urls.py`). See
[View registry#when-view_registry-is-actually-populated](../architecture/registry.md#when-view_registry-is-actually-populated)
for the ordering requirement this implies in `urls.py`.

## 5. Activate the module for a tenant

A registered view isn't reachable for a tenant until its app is explicitly activated — this is
independent of Django installation:

```python
from django_resaas.models.app import App
from django_resaas.models.entity_app import EntityApp

app, _ = App.objects.get_or_create(name="your_app", defaults={"state": "Active"})
EntityApp.objects.get_or_create(entity=my_entity, app=app, defaults={"state": "Active"})
```

> [!WARNING]
> Without this, every request to `your_app`'s endpoints 403s for that tenant before the
> queryset is ever touched — see
> [BaseAPIView#module-activation](../api/base-api-view.md#module-activation).

## 6. Permissions

Nothing to write by hand for the standard CRUD codenames — they're generated automatically once
this resource's app has migrated:

- Django's own `post_migrate` signal creates `add_<model>`/`change_<model>`/`delete_<model>`/
  `view_<model>` for every model (standard Django behavior).
- `django_resaas`'s own signal adds `list_<model>`/`pdf_<model>`/`pdf_list_<model>`/
  `restore_<model>`/`hard_delete_<model>` — but only once at least one `EntityType` exists, which
  is why [Installation](../getting-started/installation.md) runs `migrate` a second time after
  `create_entity`.
- Any `@resaas_action` gets its own `<action>_<model>` permission (or an explicit shared one) —
  see step 3 above.

Confirm the codenames you expect exist (`Permission.objects.filter(content_type__model=...)`), and
grant them to the relevant group — see [Permissions](../security/permissions.md) for how
`isPermited()`/`check_permission()` resolve a user's group to a codename.

## 7. Tests

At minimum, cover: entity isolation, branch isolation, search, filters, create, update, soft
delete/restore, and permissions (both "has it" and "doesn't have it" cases). The framework's own
test suite is the reference pattern to follow — see `src/django_resaas/tests/test_tenant.py`,
`test_soft_delete.py`, `test_module_activation.py`, `test_permissions.py` and
`test_action_sync.py`, or the fully worked example in
[`src/dev/demo/tests/test_flow.py`](../../src/dev/demo/tests/test_flow.py) (the same flow as
[Quick start](../getting-started/quick-start.md), as an executable test).

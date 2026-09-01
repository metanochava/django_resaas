# Creating a New Backend Resource

## 1. Model

``` python
class Patient(...):
    ...

    class RESAAS:
        search_fields = ["nid"]
        crud = True
```

## 2. Serializer

Create a serializer for the model, reusing the framework's base classes
whenever possible.

## 3. View

``` python
@registerView("patients")
class PatientAPIView(BaseAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
```

`register_view` is the same decorator under a PEP 8-consistent name
(`registerView = register_view`) - use whichever you like, both stay
supported.

### Custom actions (`@resaas_action`)

``` python
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

The decorator only attaches metadata to the method; `ActionSyncService`
(run from `post_migrate` and `manage.py sync_actions`) is what actually
creates/updates the `ModelExtraAction` row and the Django `Permission`.

- **Permission ownership**: if `permission=` is omitted, the codename
  defaults to `f"{action_name}_{model_name}"`. Passing `permission=`
  explicitly lets an action reuse a permission that already exists on
  the same model (e.g. two actions sharing one "can manage" gate) - the
  lookup is always scoped to the model's own `ContentType`, so a
  same-named permission on an unrelated model is never reused by
  mistake, and a shared/explicit permission's `.name` is never
  auto-rewritten (unlike the default-convention case, where it IS kept
  in sync with the action's label/model as long as the permission is
  RESAAS-managed).
- **Manual vs. decorator**: a `ModelExtraAction` row with
  `managed_by="manual"` (the default for anything created outside
  `ActionSyncService`, e.g. by hand via the admin) can never be
  silently taken over by a decorator of the same `app.model.action` -
  syncing raises `ImproperlyConfigured` instead. To hand an action over
  to the decorator on purpose, set `managed_by="decorator"` on the
  existing row yourself first.
- **Multiple views, one model**: two different views can each declare
  actions for the same model without stepping on each other - orphan
  removal only happens in `sync_registry()` (the `post_migrate`/
  `sync_actions` entry point), which aggregates every registered view's
  actions before deciding what no longer exists. Calling `sync_view()`
  directly on a single view only upserts; it never deletes.

## 4. Routes

Register the view on the router used by the application.

## 5. Permissions

Confirm that the necessary codenames exist for list, view, add, change
and delete.

## 6. Tests

Test at least: - entity isolation; - branch isolation; - search; -
filters; - creation; - update; - removal; - permissions.

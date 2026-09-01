# View registry

Every `BaseAPIView` subclass registers itself with `@register_view(name=None, module=None)`
(`core/base/views.py`). `registerView` is the original camelCase name every
existing call site uses (`hr/views/*.py` and friends) and remains a plain
alias - `registerView = register_view` - so nothing breaks; new code can
use either.

```python
@register_view("patients")
class PatientAPIView(BaseAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
```

## What the decorator does

```python
VIEW_REGISTRY: dict[str, dict[str, type]] = {}

def register_view(name=None, module=None):
    def decorator(cls):
        key = name or cls.__name__.lower().replace('apiview', '') + 's'
        module_name = module or cls.__module__.split(".")[0]
        VIEW_REGISTRY.setdefault(module_name, {})[key] = cls
        cls.module_name = module_name  # used by BaseAPIView.initial() - see api/base-api-view.md
        return cls
    return decorator
```

Two independent things happen: the class is added to `VIEW_REGISTRY`
(`{module_name: {key: ViewClass}}`), and `cls.module_name` is set - the
same attribute `BaseAPIView.initial()` checks against `EntityApp` for
module activation.

## The chain: View -> VIEW_REGISTRY -> ActionSyncService -> Schema

```text
@register_view + @resaas_action
        |
        v
   VIEW_REGISTRY               (populated at import time - see the
        |                       "when is this actually populated" note below)
        v
ActionSyncService.sync_registry(VIEW_REGISTRY)
        |                       (post_migrate signal / manage.py sync_actions)
        v
  ModelExtraAction + Permission   (see ../security/permissions.md for
        |                          the manual/decorator ownership rules)
        v
ResaasSchemaBuilder.build()      (per model, at request time - see
        |                          schema-contract.md)
        v
  Schema 1.0 "actions"
        |
        v
   quasar_resaas (frontend)
```

## When `VIEW_REGISTRY` is actually populated

`@register_view` only runs when its module is *imported*. `dev/urls.py`
imports every view (directly or via each app's own `views/__init__.py`,
e.g. `hr/views/__init__.py`) as a side effect of building the router -
see the comment at the top of `dev/urls.py` for why `build_saas_urls()`
specifically runs *after* the `include(...)` calls. A process that never
touches `ROOT_URLCONF` (a bare `manage.py migrate`, for instance) may
never populate `VIEW_REGISTRY` at all, in which case
`sync_resaas_actions` (the `post_migrate` receiver) silently no-ops -
this is a known limitation, not something this phase changed.

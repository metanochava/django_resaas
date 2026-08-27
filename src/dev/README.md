# dev — the runnable example project

This is the runnable Django project used for local development and as the **minimal example
application** that proves the full `django_resaas` flow end to end: a model with a `RESAAS`
config → `BaseSerializer` → `BaseAPIView` → multi-tenant/RBAC enforcement → `ResaasSchemaBuilder`
→ a real HTTP response — using nothing but the same public patterns documented in
[`docs/development/creating-resource.md`](../docs/development/creating-resource.md).

It wires up `django_resaas` and `hr` (the framework's own optional module), plus one extra app
written just for this purpose: [`dev/demo`](demo/) — a single `Product` model. See
[`docs/api/schema-contract.md`](../docs/api/schema-contract.md) for what its schema endpoint
returns, and [`src/dev/demo/tests/test_flow.py`](demo/tests/test_flow.py) for the executable
version of everything below — that test is what CI actually runs.

```python
# dev/demo/models.py
class Product(BaseModel):          # entity/branch, soft delete, created/updated_by - all free
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "sku"]
        crud = True
        icon = "mdi-package-variant"
```

```python
# dev/demo/views.py
@registerView(module="demo")
class ProductAPIView(BaseAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

That's the whole app. It gets full CRUD, pagination, ordering, `?search=`, soft delete/restore,
and a schema endpoint automatically.

## Quickstart

```bash
cp .env.example .env          # optional - sane dev defaults apply either way
pip install -e ".[dev]"
python src/manage.py migrate
python src/manage.py create_entity   # interactive: creates a superuser + tenant + "Admin" group
python src/manage.py migrate         # yes, again - see note below
python src/manage.py runserver 0.0.0.0:7002
```

The second `migrate` is not a typo: the CRUD permissions (`list_product`, `add_product`, ...) are
created by a `post_migrate` signal (`core/signals/permissions.py`) that no-ops until at least one
`EntityType` exists - which `create_entity` is what creates it. Re-running `migrate` (idempotent,
applies no new migrations) fires that signal again now that the guard condition is met. Without
this, every request fails RBAC with no permissions to grant to any group.

`create_entity` only activates the `hr` module for the new tenant by default. To exercise the
demo app too, activate its module the same way any per-client module would be in a real
deployment — this is exactly what `test_flow.py`'s `tenant_client` fixture automates for tests:

```python
from django_resaas.models.app import App
from django_resaas.models.entity_app import EntityApp

demo_app, _ = App.objects.get_or_create(name="demo", defaults={"state": "Active"})
EntityApp.objects.get_or_create(entity=my_entity, app=demo_app, defaults={"state": "Active"})
```

## Trying the demo app by hand

**1. Log in** to get a JWT (`identifier` is the email or username you gave `create_entity`):

```bash
curl -X POST http://localhost:7002/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "you@example.com", "password": "..."}'
# -> {"access": "...", "refresh": "...", ...}
```

**2. Issue a signed tenant context** (see
[`docs/architecture/multi-tenancy.md`](../docs/architecture/multi-tenancy.md)):

```bash
curl -X POST http://localhost:7002/api/resaas/context/ \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d '{"entity_id": "<entity-uuid>", "branch_id": "<branch-uuid>", "group_id": "<root-group-uuid>"}'
# -> {"token": "<context-token>", "context": {...}}
```

**3. Every subsequent request** needs three headers:

```
Authorization: Bearer <jwt>
X-RESAAS-Context: <signed context token>
L: 1
```

```bash
# schema - what the frontend needs to render this resource
curl -H "Authorization: Bearer $JWT" -H "X-RESAAS-Context: $CTX" -H "L: 1" \
     http://localhost:7002/api/django_resaas/resaasapps/demo/product/schema/

# list / create - all three headers required
curl -H "Authorization: Bearer $JWT" -H "X-RESAAS-Context: $CTX" -H "L: 1" \
     http://localhost:7002/api/demo/products/

curl -X POST -H "Authorization: Bearer $JWT" -H "X-RESAAS-Context: $CTX" -H "L: 1" \
     -H "Content-Type: application/json" \
     -d '{"name": "Widget", "sku": "WID-1", "price": "9.99"}' \
     http://localhost:7002/api/demo/products/
```

## What this proves

- **Multi-tenancy**: `Product` inherits `entity`/`branch` from `BaseModel` and is automatically
  scoped to the tenant in the request's signed context.
- **RBAC**: the request is rejected unless the user's group has the auto-generated
  `list_product`/`add_product`/... permission for the active branch (see
  `docs/security/permissions.md`).
- **Soft delete**: `DELETE` doesn't remove the row; `?objects=all` and `POST .../restore/` bring
  it back (see `docs/features/soft-delete.md`).
- **Dynamic search**: `?search=widget` matches `RESAAS.search_fields`.
- **The Schema 1.0 contract**: the schema endpoint's response matches
  `docs/api/schema-contract.md` exactly — `ui.icon`, `filters.search_fields`, and `model.endpoint`
  all come straight from `Product`'s `RESAAS` config.

## Database

Defaults to a local `db.sqlite3` file. Set `SQL_ENGINE`/`SQL_DATABASE`/`SQL_USER`/`SQL_PASSWORD`/
`SQL_HOST`/`SQL_PORT` in `.env` to point at Postgres instead.

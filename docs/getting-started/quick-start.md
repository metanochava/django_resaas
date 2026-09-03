# Quick Start

A guided walk through the full `django_resaas` flow, end to end: one model → full CRUD API,
scoped by tenant, authorized by permission, described by a schema — with nothing hand-written
beyond the model, its serializer and its view. This mirrors the framework's own example app,
[`dev/demo`](../../src/dev/demo), whose behavior is asserted by
[`dev/demo/tests/test_flow.py`](../../src/dev/demo/tests/test_flow.py) — that test is what CI
actually runs against this exact flow.

Complete [Installation](installation.md) first.

## 1. Model

```python
# your_app/models/product.py
from django.db import models
from django_resaas.core.base.models import BaseModel

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

```bash
python manage.py makemigrations your_app
python manage.py migrate
```

See [Models & RESAAS](../models/resaas-config.md) for every `class RESAAS` attribute.

## 2. Serializer

```python
# your_app/serializers/product.py
from django_resaas.core.base.serializers import BaseSerializer
from your_app.models.product import Product

class ProductSerializer(BaseSerializer):
    class Meta:
        model = Product
        fields = "__all__"
```

`BaseSerializer` already marks `id`/`entity`/`branch`/`created_by`/`updated_by`/`created_at`/
`updated_at`/`deleted_at` read-only — see
[Public API reference](../api/public-api-reference.md#baseserializer---django_resaascorebaseserializersbaseserializer).

## 3. View

```python
# your_app/views/product.py
from django_resaas.core.base.views import BaseAPIView, register_view
from your_app.models.product import Product
from your_app.serializers.product import ProductSerializer

@register_view(module="your_app")
class ProductAPIView(BaseAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

That's the whole app. It already has full CRUD, pagination, ordering, `?search=`, soft
delete/restore/hard delete, and a schema endpoint — see
[Creating a new resource](../development/creating-resource.md) for the complete walkthrough
(custom actions, routing, permissions, tests) and [BaseAPIView](../api/base-api-view.md) for what
each of those does under the hood.

## 4. Activate the module for a tenant

An app only becomes usable for a tenant once explicitly activated. `create_entity` (from
Installation) only activates `hr` by default — any other app, including this one, needs the same
treatment:

```python
from django_resaas.models.app import App
from django_resaas.models.entity_app import EntityApp

app, _ = App.objects.get_or_create(name="your_app", defaults={"state": "Active"})
EntityApp.objects.get_or_create(entity=my_entity, app=app, defaults={"state": "Active"})
```

> [!WARNING]
> Without this, `BaseAPIView.initial()` rejects every request to `your_app`'s endpoints with
> a 403, for every tenant that hasn't run it — see
> [BaseAPIView#module-activation](../api/base-api-view.md#module-activation).

## 5. Call it

Every authenticated request needs three headers: a JWT, a signed tenant context, and a language
id. Get the first two once:

```bash
# 1. log in
curl -X POST http://localhost:7002/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "you@example.com", "password": "..."}'
# -> {"access": "...", "refresh": "...", ...}

# 2. issue a signed tenant context (entity/branch/group you created via create_entity)
curl -X POST http://localhost:7002/api/resaas/context/ \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d '{"entity_id": "<entity-uuid>", "branch_id": "<branch-uuid>", "group_id": "<root-group-uuid>"}'
# -> {"token": "<context-token>", "context": {...}}
```

Then, on every request:

```bash
# schema - what a frontend needs to render this resource
curl -H "Authorization: Bearer $JWT" -H "X-RESAAS-Context: $CTX" -H "L: 1" \
     http://localhost:7002/api/django_resaas/resaasapps/your_app/product/schema/

# list
curl -H "Authorization: Bearer $JWT" -H "X-RESAAS-Context: $CTX" -H "L: 1" \
     http://localhost:7002/api/your_app/products/

# create
curl -X POST -H "Authorization: Bearer $JWT" -H "X-RESAAS-Context: $CTX" -H "L: 1" \
     -H "Content-Type: application/json" \
     -d '{"name": "Widget", "sku": "WID-1", "price": "9.99"}' \
     http://localhost:7002/api/your_app/products/
```

See [Multi-tenancy](../architecture/multi-tenancy.md) for what the context token carries and how
it's validated on every request.

## What this proves

- **Multi-tenancy** — `Product` inherits `entity`/`branch` from `BaseModel` and is automatically
  scoped to the tenant in the request's signed context; see
  [Multi-tenancy](../architecture/multi-tenancy.md).
- **Authorization** — the request is rejected unless the user's group has the auto-generated
  `list_product`/`add_product`/... permission for the active branch; see
  [Permissions](../security/permissions.md).
- **Soft delete** — `DELETE` doesn't remove the row; `?objects=all` and `POST .../restore/` bring
  it back; see [Soft delete](../features/soft-delete.md).
- **Dynamic search** — `?search=widget` matches `RESAAS.search_fields`; see
  [Search](../api/search.md).
- **The Schema 1.0 contract** — the schema endpoint's response matches
  [Schema 1.0 contract](../api/schema-contract.md) exactly: `ui.icon`, `filters.search_fields` and
  `model.endpoint` all come straight from `Product`'s `RESAAS` config.

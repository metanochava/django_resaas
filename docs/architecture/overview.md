# Backend Architecture

`django_resaas` layers a small set of shared base classes on top of Django/DRF so that every
resource gets multi-tenancy, permissions, soft delete, search, filters, pagination and a
machine-readable schema for free, instead of each app reimplementing them.

```text
Client / Frontend
       |
       v
 X-RESAAS-Context, L headers
       |
       v
TenantContextMiddleware        (architecture/middleware.md)
       |
       v
     Router                    (VIEW_REGISTRY -> build_saas_urls() - architecture/registry.md)
       |
       v
   BaseAPIView                 (api/base-api-view.md)
       |
       +---- initial(): module active? permission granted?  (security/permissions.md)
       +---- get_queryset(): entity/branch scoping, ?objects=, ?search=
       |
       v
   BaseSerializer               (api/public-api-reference.md)
       |
       v
     Model                      (BaseModel / TimeModel / SoftBaseModel)
       |
       v
    Database
```

## Responsibilities

### Middleware

`TenantContextMiddleware` decodes the signed `X-RESAAS-Context` header into
`request.entity_id`/`branch_id`/`entity_type_id`/`group_id` and the `L` header into
`request.lang_id`, on every request, before any view code runs. `FileAccessMiddleware` separately
gates direct access to uploaded media. See [Middleware](middleware.md).

### View (`BaseAPIView`)

Receives the request, confirms the tenant's module is active and the user is authorized
(`initial()`), builds a tenant-scoped, optionally soft-delete-aware, optionally searched queryset
(`get_queryset()`), and coordinates the serializer and response. See
[BaseAPIView](../api/base-api-view.md).

### Serializer (`BaseSerializer`)

Validates input data and turns Django instances into API-shaped data, with `entity`/`branch`/
`created_by`/`updated_by`/timestamps read-only by default. See
[Public API reference](../api/public-api-reference.md).

### Model (`BaseModel`)

Represents persistent data. `BaseModel` (via `TimeModel`/`SoftBaseModel`) adds tenant scoping,
soft delete, and audit fields to any model that inherits it — see
[Multi-tenancy](multi-tenancy.md).

### Schema (`ResaasSchemaBuilder`)

Turns a model plus its serializer fields into the declarative Schema 1.0 JSON contract a frontend
consumes to render a whole CRUD screen without hardcoding conventions client-side. See
[Schema 1.0 contract](../api/schema-contract.md).

## Where to go next

- New to the framework: [Installation](../getting-started/installation.md) then
  [Quick start](../getting-started/quick-start.md).
- Adding a resource to an existing project: [Creating a new resource](../development/creating-resource.md).
- Understanding tenant isolation in depth: [Multi-tenancy](multi-tenancy.md) and
  [Request lifecycle](request-lifecycle.md).

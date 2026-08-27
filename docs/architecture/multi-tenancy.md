# Multi-tenancy

RESAAS works with a tenant context. A request can carry:

-   `entity_type_id`
-   `entity_id`
-   `branch_id`
-   `group_id`
-   `lang_id`

## Main rule

A model that has `entity_id` must be filtered by the active entity.
A model that has `branch_id` must also be filtered by the active branch.

Conceptual example:

``` python
if hasattr(Model, "entity_id"):
    qs = qs.filter(entity_id=self.request.entity_id)

if hasattr(Model, "branch_id"):
    qs = qs.filter(branch_id=self.request.branch_id)
```

When the manager is swapped, for example to `all_objects` or
`deleted_objects`, the tenant filters must be reapplied.

## Purpose

The goal is to prevent a request from one entity from accidentally
accessing data belonging to another entity.

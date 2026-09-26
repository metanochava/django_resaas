# Dynamic Search

Every `BaseAPIView` list/retrieve endpoint accepts a `?search=` query parameter, applied in
`get_queryset()` via `build_search_query()` (`core/base/views.py`):

```text
GET /api/django_resaas/persons/?search=metano&page=1&page_size=10
```

An empty or missing `search` value returns an empty `Q()`, which is skipped — it never turns into
`qs.filter(Q())`, which would match nothing being filtered rather than everything being excluded.

## With `RESAAS.search_fields` declared

```python
class RESAAS:
    search_fields = ["name", "surname"]
```

produces, for `?search=metano`:

```python
Q(name__icontains="metano") | Q(surname__icontains="metano")
```

Each declared field is validated (`is_valid_search_field()`) before being used — an invalid or
mistyped field name is silently skipped rather than raising, so a typo in `search_fields` doesn't
break the whole endpoint, it just quietly excludes that field from search.

## Relation traversal

A `search_fields` entry can walk relations with `__`, as long as every step except the last is
itself a relation and the final step is a `Char`/`Text`/`Email` field:

```python
class RESAAS:
    search_fields = [
        "code",
        "employee__person__full_name",
    ]
```

## Without `search_fields` (automatic fallback)

If the model declares no `RESAAS.search_fields`, search falls back to every direct
`CharField`/`TextField`/`EmailField` **on the model itself** — this fallback does **not** traverse
relations or match on a related object's name. A model that needs search across a foreign key
must declare `search_fields` explicitly.

## Usage example

```text
GET /api/django_resaas/persons/?search=m&page=1&page_size=10
```

Combine with filters and pagination — see [Filters, ordering and pagination](filters-pagination.md).

## Relation picker (`GET /api/django_resaas/relations/`)

`RelationsAPIView` (`saas/management/apicommands/view/app_schema.py`) feeds the
relation selects of automatic forms (quasar_resaas `utils/autoForm.js`) and of
manual ones:

```text
GET /api/django_resaas/relations/?model=app_label.ModelName&search=abc
-> [{"id": ..., "value": ..., "label": ...}, ...]   (at most 50, newest first)
```

It returns only `id`, `value` and `label`, never the record. `search` follows
the rules above (`RESAAS.search_fields`, else the fallback).

**Security: PROTECTED** (`IsAuthenticated`). For a RESAAS model (one that
declares `class RESAAS`), the current signed context (`X-RESAAS-Context`) must
grant **one** of these permissions:

| Permission | Why |
|---|---|
| `list_<model>` / `view_<model>` | the caller can already read the model |
| `add_<owner>` / `change_<owner>` of any RESAAS model with an **editable** FK / O2O / M2M to it | the caller fills a form that has this field, e.g. `add_branchusergroup` → pick a `User` |

The audit columns (`created_by`, `updated_by`, `deleted_by`) do not count.
They point to `User` from every model, so being able to write a record is not
a reason to list users. Without any of these permissions the answer is
`403 {"error": {...}}`. A malformed `model` gets `400` with
`error.details.model`.

**Multi-tenancy:** only rows of the current Entity are returned: by
`entity_id` when the model has it, and for `User` by membership of the current
Entity (`EntityUser`). A user of another Entity is never listed, even with
`list_user`. Knowing an id does not help: the endpoint only lists.

Plain framework models (`auth.Permission`, `contenttypes.ContentType`, ...)
have no tenant or permission conventions, and keep the previous behaviour
(any authenticated user).

**Troubleshooting:** a select that answers `403` means the user's group has
neither read permission on the related model nor add/change permission on a
model that references it. Grant the permission that matches the form (e.g.
`add_leaverequest` for the "approved by" picker). Do not make the endpoint
public.

Tests: `saas/tests/test_relations_endpoint.py`, `saas/tests/test_relation_engine.py`.

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

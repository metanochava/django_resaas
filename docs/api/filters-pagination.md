# Filters, Ordering and Pagination

## Filters

Filtering is **fully automatic** — there is no `filterset_fields` to declare per view.
`DynamicFilterBackend` (`core/base/views.py`) builds a `django_filters.FilterSet` at request time
from every field on the model **except** `FileField`/`ImageField`, using exact-match lookups:

```text
GET /api/hr/employees/?state=Active
```

Any model field is filterable this way the moment the model exists — including foreign keys (by
their id) and booleans/dates by exact value. There's no per-model opt-in or configuration.

## Combining with search

Search (`?search=`) and filters compose freely — search is applied as an additional `Q()` on top
of whatever `DynamicFilterBackend`/`DjangoFilterBackend` already filtered:

```text
GET /api/hr/employees/?search=dias&state=Active&page=1&page_size=10
```

## Ordering

`ordering_fields = "__all__"` is set on `BaseAPIView`, so any model field can be used with DRF's
standard `OrderingFilter` query param:

```text
GET /api/hr/employees/?ordering=-created_at
```

## Pagination

`ResaasPagination` (a `PageNumberPagination` subclass) is the default pagination class:

- `page` — page number.
- `page_size` — rows per page. Default `10` (`REST_FRAMEWORK["PAGE_SIZE"]`), capped at
  `max_page_size = 1000`. A model can override its own default via `RESAAS.pagination` — see
  [Models & RESAAS](../models/resaas-config.md).
- `page_size=0` is a special case: it disables pagination entirely for that request and returns
  every matching row in a single response, still shaped like a paginated one
  (`{"count", "next": null, "previous": null, "results"}`) so a client doesn't need a separate
  code path. Use sparingly — it bypasses the page-size cap.

The response envelope (`count`/`next`/`previous`/`results`) is always DRF's standard
`PageNumberPagination` shape, including in the `page_size=0` case above. See
[Schema 1.0 contract](schema-contract.md#shape) for how a model's effective pagination defaults
(`page_size`, `page_size_options`, `default_ordering`) are exposed to a frontend without it having
to know any of the above.

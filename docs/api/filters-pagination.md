# Filters, Ordering and Pagination

## Filters

`DjangoFilterBackend` allows filtering by query parameters for eligible
fields.

Example:

``` text
?state=Active
```

## Combining

Search and filters can be combined:

``` text
?search=dias&state=Active&page=1&page_size=10
```

## Ordering

When `ordering_fields = "__all__"` is active, the allowed fields can be
used by DRF's ordering mechanism.

## Pagination

Usual parameters:

-   `page`
-   `page_size`

The paginated response must keep the structure defined by the project's
global configuration.

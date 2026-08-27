# BaseAPIView

`BaseAPIView` is the common base for the REST APIs.

## Main responsibilities

-   CRUD through `ModelViewSet`;
-   filters;
-   ordering;
-   dynamic search;
-   permissions;
-   multi-tenancy;
-   auditing;
-   soft delete;
-   restore;
-   hard delete;
-   select mode.

## Permission mapping

Example:

``` python
permission_action_map = {
    "list": "list",
    "retrieve": "view",
    "create": "add",
    "update": "change",
    "partial_update": "change",
    "destroy": "delete",
    "restore": "restore",
    "hard_delete": "hard_delete",
}
```

For a `Patient` model, creation may require `add_patient`, updating
`change_patient` and removal `delete_patient`.

## Queryset

`get_queryset()` must be the central point that guarantees tenant
isolation before listing and search.

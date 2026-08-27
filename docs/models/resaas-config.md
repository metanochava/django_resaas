# RESAAS Configuration on Models

Models can declare framework-specific metadata through `class RESAAS`.

Example:

``` python
class RESAAS:
    label_field = "name surname"
    search_fields = ["name", "surname"]
    crud = True
```

## `label_field`

Defines the fields used to build a human-readable representation of the
instance.

## `search_fields`

Explicitly defines the fields on which text search should operate.

## `crud`

Indicates that the resource participates in the framework's CRUD
mechanism, when that option is used by the application.

## Recommendation

When a model needs controlled search, declare `search_fields` explicitly
instead of relying on a generic fallback.

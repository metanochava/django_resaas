# Models & `class RESAAS`

Any model can declare a nested `class RESAAS` to configure how the framework treats it — search,
labeling, and every overridable section of the [Schema 1.0 contract](../api/schema-contract.md).
Every attribute is optional; the framework falls back to a sane default for anything you don't
set. Nothing here does anything unless the model also has a registered view — see
[Creating a new resource](../development/creating-resource.md).

```python
class Product(BaseModel):
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50)

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "sku"]
        crud = True
        icon = "mdi-package-variant"
```

## `label_field` / `value_field`

`label_field` (string) names the field(s) used to build a human-readable representation of an
instance — for select/autocomplete options, PDF titles, etc. Multiple fields are supported,
separated by a space, comma or pipe:

```python
class RESAAS:
    label_field = "name surname"   # -> ["name", "surname"], joined at render time
```

`value_field` defaults to `"id"` and rarely needs overriding — it's the field used as the
underlying value in the same label/value representation.

## `search_fields`

Explicit list of fields `?search=` should match (`icontains`, OR'd together). Supports relation
traversal with Django's `__` lookup syntax, as long as every step except the last is a relation
field and the last step is a `Char`/`Text`/`Email` field:

```python
class RESAAS:
    search_fields = ["code", "employee__person__full_name"]
```

If omitted, search falls back to every direct `Char`/`Text`/`Email` field **on the model itself**
— it does not traverse relations in fallback mode. Declare `search_fields` explicitly whenever
searching across a relation matters. Full behavior in [Search](../api/search.md).

## `crud`

Boolean, default `True`. Feeds `ui.crud` in the schema — a frontend convention for "show the
standard CRUD screen for this model." Setting it to `False` doesn't disable the API itself, only
signals to a schema-driven UI that this model isn't meant to get a generic CRUD screen.

## `icon`

String (e.g. a Quasar/Material icon name like `"mdi-package-variant"`), fed straight into
`ui.icon` in the schema. `None` if unset.

## `routes`

Dict overriding the default `{verb}_{model}` route-name convention — merged over the default, not
replaced (setting one key leaves the others at their default):

```python
class RESAAS:
    routes = {"list": "browse_product"}   # only "list" changes; add/change/view stay default
```

## `ui`, `filters`, `pagination`, `pdf`

Each is a dict, shallow-merged over its section's defaults in the schema — see
[Schema 1.0 contract](../api/schema-contract.md) for the exact default shape of each and what
every key controls. For example, to change the default page size and disable the PDF list export
for one model:

```python
class RESAAS:
    pagination = {"page_size": 25}
    pdf = {"list": False}
```

## Recommendation

Declare `search_fields` explicitly on any model with more than a couple of text fields, or where
search across a relation matters — relying on the automatic fallback silently changes behavior
the moment a new `CharField` is added to the model.

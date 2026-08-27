# Dynamic Search

The API receives the search term via:

``` text
?search=metano
```

## Configured fields

If the model has:

``` python
class RESAAS:
    search_fields = ["name", "surname"]
```

the search should produce conditions equivalent to:

``` python
Q(name__icontains="metano") |
Q(surname__icontains="metano")
```

## Relations

When supported by the field validator, a configuration can use paths
such as:

``` python
search_fields = [
    "code",
    "employee__person__full_name",
]
```

## Empty query

It's important not to turn an invalid search into an empty `Q()`
followed by `qs.filter(Q())`, since that doesn't restrict the queryset
at all.

## Usage example

``` text
/api/django_resaas/persons?search=m&page=1&page_size=10
```

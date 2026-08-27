# Backend Troubleshooting

## Search returns every record

Check:

1.  whether `search` arrives in `request.query_params`;
2.  whether `RESAAS.search_fields` is being read;
3.  whether the `Q` object actually contains conditions;
4.  whether another backend isn't overriding the behavior;
5.  the final SQL via `print(qs.query)`.

## Release already exists

Message:

``` text
Fatal: There is an existing release branch
```

Resolve the existing release before starting another one.

## Permission denied

Confirm: - module active; - correct entity; - codename; - user/group
association; - the result of `isPermited()`.

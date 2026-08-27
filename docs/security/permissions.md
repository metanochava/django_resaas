# Permissions

The backend is the final authority for authorization.

## Process

1.  Identify the view's action.
2.  Convert the action into a permission prefix.
3.  Get the model's technical name.
4.  Build the codename.
5.  Check it with `isPermited()`.

Example:

``` text
create + patient -> add_patient
update + patient -> change_patient
destroy + patient -> delete_patient
```

## Cache

A per-request cache can avoid repeated checks of the same codename
during the same request.

## Module

Besides the permission itself, the application can check whether the
corresponding module is active for the entity.

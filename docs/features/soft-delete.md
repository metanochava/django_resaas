# Soft Delete, Restore and Hard Delete

## Soft delete

Instead of immediately deleting a record, the system can mark
`deleted_at`.

## Listing

The `objects` parameter can select different managers:

``` text
?objects=all
?objects=deleted
```

After switching managers, the entity and branch filters must be
reapplied.

## Restore

A `restore` action recovers a deleted instance, provided the user has
the corresponding permission.

## Hard delete

`hard_delete` permanently removes the instance. It must be protected by
a specific permission.

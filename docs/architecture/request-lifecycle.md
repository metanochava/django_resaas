# Request Lifecycle

``` text
HTTP Request
   |
   v
initial()
   |
   +-- checks module
   +-- determines permission
   +-- checks authorization
   |
   v
get_queryset()
   |
   +-- entity
   +-- branch
   +-- objects=all/deleted
   +-- search
   |
   v
DjangoFilterBackend / Ordering
   |
   v
Serializer
   |
   v
Model / Database
   |
   v
HTTP Response
```

## Create

On creation, `perform_create()` can automatically fill in `created_by`,
`updated_by`, `entity_id` and `branch_id`.

## Update

On update, `perform_update()` must update the user responsible for the
change.

## Delete

When the model supports soft delete, logical removal must preserve the
record for later recovery.

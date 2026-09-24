# Field-level permissions

Some fields are more sensitive than the record that holds them. A user who may see an
employee's contract (`view_contract`) should not automatically see its salary. Field-level
permissions gate **individual fields** with their own permission, **on top of** the model's
normal action permission ([Permissions](permissions.md)), never instead of it.

Implementation: `src/django_resaas/saas/core/base/field_access.py` (resolution),
`saas/core/base/mixins/serializer/field_permissions.py` (serializer enforcement, part of
`BaseSerializer`). Tests: `src/django_resaas/hr/tests/test_field_permissions.py`.

## Declaring a restricted field

Use the existing per-field metadata, `RESAAS.fields` ([Models & `class RESAAS`](../models/resaas-config.md)),
with a `permissions` key:

```python
class Contract(BaseModel):
    salary = models.DecimalField(max_digits=12, decimal_places=2)

    class RESAAS:
        fields = {
            "salary": {
                "permissions": {
                    "view": "view_contract_salary",      # needed to READ it
                    "change": "change_contract_salary",  # needed to WRITE it
                },
            },
        }
```

- `view` is required; a `permissions` entry without it is ignored.
- `change` is optional. When it is omitted, writing requires the `view` permission.
- No code change in the view or serializer is needed: every `BaseSerializer` and every
  `BaseAPIView` apply it.

## Permissions (discovery and sync)

The codenames are created by the same `post_migrate` signal that creates the model permissions
(`saas/core/signals/permissions.py`): one `Permission` per declared codename, on the model's
content type, named `Can view <model> <field>` / `Can change <model> <field>`. Like every model
permission it is added to the **Root** group. Every other group gets it only through an explicit
grant, so an Entity can build a group that sees contracts but not salaries without any code change.

Permissions currently declared:

| Model | Field | Read | Write |
|---|---|---|---|
| `hr.Contract` | `salary` | `view_contract_salary` | `change_contract_salary` |

## What the backend enforces

Access is resolved per request with `check_permission()`: the current user, in the **signed**
Entity/Branch/Group context (`X-RESAAS-Context`). It is the same check as every action, cached
per request in `request._perm_cache`. The context never comes from the request body, so knowing an
id or sending another `group_id` does not change the result.

| Caller holds | API output | Payload with the field |
|---|---|---|
| view + change | returned | accepted |
| view only | returned | **403**, unless it re-sends the current value (see below) |
| change only | never returned | accepted |
| neither | never returned | **403** |

When a caller may not read the field, the field is also absent from:

- **Filters**: `?salary=1000` is not a filter for that caller. `DynamicFilterBackend` does not
  build it, so the query parameter is ignored.
- **Ordering**: `?ordering=-salary` is dropped (`FieldAccessOrderingFilter`), and the default
  ordering applies.
- **Search**: a restricted field listed in `RESAAS.search_fields`, including a path through a
  relation such as `contract__salary`, is skipped. The automatic text-field fallback skips it too.
- **PDF**: the detail PDF (`get_pdf_fields`) and the list PDF (`get_pdflist_context`) leave it out.

Without these, row order, filter results or search matches would reveal the value.

**No request means no access.** A serializer used without `context={"request": ...}`, for
example from a service, task, shell or management command, hides every restricted field. Pass the
request when the output is meant for a user who holds the permission.

### Writes

A write is rejected **before** validation, with the standard RESAAS error contract
(`ResaasAPIException` → `resaas_exception_handler`, `saas/core/exceptions/`):

```http
PATCH /api/hr/contracts/<id>/
{"salary": "9999.00"}

403 Forbidden
{"error": {"code": "field_permission_denied",
           "message": "You are not allowed to change these fields.",
           "details": {"fields": ["salary"]}}}
```

- `code` is stable, and `details.fields` lists the blocked field names. The message is translated
  (`Translate.tdc`, in all four languages).
- **Re-sending the current value is not a change.** An update that sends the value the record
  already holds is accepted. `BaseStore` PATCHes the whole loaded record back, so a view-only
  user can still edit the contract's other fields.
- **Required fields.** If the restricted field is required on the model (`Contract.salary` is)
  and the caller may not write it, a **create** is rejected with the same 403, whether or not the
  field was sent. The caller cannot create the record at all. This is deliberate: the alternative
  is a database error or an invented value.
- Other fields of the same record are unaffected. A PATCH that doesn't touch the restricted field
  works normally.

## Schema

The Schema 1.0 field descriptor (`/api/django_resaas/resaasapps/<app>/<model>/schema/`) carries
the codenames as **static metadata**. The schema is the same for every user:

```json
{"name": "salary", "type": "DecimalField",
 "permissions": {"view": "view_contract_salary", "change": "change_contract_salary"}}
```

The frontend compares them with the user's permissions. See quasar_resaas *Permissions → Field-level
permissions*. Hiding the field there is **UX only**. The serializer is what enforces it.

## Limits

- Protection follows the **model field**. A serializer field that exposes the value under
  another name through `source="salary"` is covered. A field built from a relation path
  (`source="contract.salary"` on another model's serializer), a `SerializerMethodField`, or a
  hand-built response is **not** covered. Don't expose a restricted value that way. Serialize
  the related record with its own `BaseSerializer` instead.
- Views that are not `BaseAPIView`, and serializers that are not `BaseSerializer`, do not apply
  the rules.
- `Contract.salary` is a reference value on the contract. What an employee is actually paid lives
  in `EmployeeSalary` / `SalaryComponent` / `Payroll`, which are separate models with their own
  model permissions (`view_employeesalary`, `view_payroll`, ...).

## Troubleshooting

**The field is missing for a user who should see it.** Check that:

1. the permission exists (it is created on `migrate`; run it again after adding the declaration);
2. the group of the **current context** holds it, not another group of the same user;
3. the serializer was given the request (`get_serializer()` in a view does this; a manual
   `MySerializer(obj)` does not).

**A save fails with `field_permission_denied`.** The payload changes a restricted field the
current group may not write, or it is a create of a record whose required restricted field the
caller may not set. Grant the `change` permission to the group. Do not remove the field
declaration.

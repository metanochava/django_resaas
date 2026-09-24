"""Field-level authorization.

A model marks a sensitive field in its existing RESAAS.fields metadata:

    class RESAAS:
        fields = {
            "salary": {
                "permissions": {
                    "view": "view_contract_salary",
                    "change": "change_contract_salary",
                },
            },
        }

- "view" is required to READ the field (API output, filters, ordering,
  search, PDFs).
- "change" is required to WRITE it (create/update payloads). When omitted,
  writing requires the "view" permission.

The permissions are created by the post_migrate permission signal
(core/signals/permissions.py) and resolved with the same effective-permission
check as every other action (check_permission: current user + signed
Entity/Branch/Group context). They are layered ON TOP of the model's normal
action permission (view_contract, change_contract, ...), never instead of it.

Without a request (a service, task or shell serializing a record) access is
denied: the field is hidden, never exposed by default.
"""

from django_resaas.saas.core.base.permissions import check_permission


def get_field_permissions(Model):
    """{field_name: {"view": codename, "change": codename}} for every field
    the model restricts. Empty for models without restrictions."""

    resaas = getattr(Model, "RESAAS", None)
    fields = getattr(resaas, "fields", None) or {}

    restricted = {}

    for name, config in fields.items():
        permissions = (config or {}).get("permissions") or {}
        view = permissions.get("view")

        if not view:
            continue

        restricted[name] = {
            "view": view,
            "change": permissions.get("change") or view,
        }

    return restricted


def has_permission_cached(request, codename):
    """check_permission() with the same per-request cache BaseAPIView.initial()
    already keeps (request._perm_cache)."""

    if request is None:
        return False

    cache = getattr(request, "_perm_cache", None)

    if cache is None:
        cache = {}
        try:
            request._perm_cache = cache
        except AttributeError:
            pass

    if codename not in cache:
        try:
            cache[codename] = check_permission(request=request, role=codename)
        except AttributeError:
            # not a tenant-aware request (no entity/branch/group resolved)
            cache[codename] = False

    return cache[codename]


def unreadable_fields(request, Model):
    """Names of the restricted fields the request may NOT read."""

    return {
        name
        for name, perms in get_field_permissions(Model).items()
        if not has_permission_cached(request, perms["view"])
    }


def unwritable_fields(request, Model):
    """Names of the restricted fields the request may NOT write."""

    return {
        name
        for name, perms in get_field_permissions(Model).items()
        if not has_permission_cached(request, perms["change"])
    }


def is_path_readable(request, Model, path):
    """False when any step of a lookup path (salary, employee__contracts__salary,
    -salary) crosses a field the request may not read."""

    from django.core.exceptions import FieldDoesNotExist

    current = Model

    for part in str(path).lstrip("-").split("__"):
        if current is None:
            return True

        if part in unreadable_fields(request, current):
            return False

        try:
            field = current._meta.get_field(part)
        except FieldDoesNotExist:
            return True

        current = field.related_model if field.is_relation else None

    return True

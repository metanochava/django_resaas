"""Field-level authorization.

A model marks a sensitive field in its existing RESAAS.fields metadata:

    class RESAAS:
        fields = {
            "amount": {
                "permissions": {
                    "view": "view_agreement_amount",
                    "change": "change_agreement_amount",
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
action permission (view_agreement, change_agreement, ...), never instead of it.

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


# The tenant fields are read by ROLE, not by codename: the Entity is returned
# only to the platform Root, the Branch only to an Entity administrator (Admin).
# Only READING is restricted. Writes keep using the signed context, so creating
# a record in the current Branch still works for whoever may create it.
TENANT_READ_ROLES = {
    "entity": "role:platform",
    "branch": "role:platform_or_entity_admin",
}

# a role is true when any of its checks (group_access_service) is true
_ROLE_CHECKS = {
    "role:platform": ("is_platform",),
    "role:entity_admin": ("is_entity_admin",),
    "role:platform_or_entity_admin": ("is_platform", "is_entity_admin"),
}


def _is_relation(Model, name):
    from django.core.exceptions import FieldDoesNotExist

    try:
        return Model._meta.get_field(name).is_relation
    except FieldDoesNotExist:
        return False


def hidden_tenant_fields(request, Model):
    """The tenant fields (entity, branch) this request's role may not read.
    Only these leave the schema: the codename-restricted fields stay, because
    the frontend shows them write-only and checks them with User.can()."""

    return {
        name
        for name, role in TENANT_READ_ROLES.items()
        if _is_relation(Model, name) and not rule_allowed(request, role)
    }


def get_field_restrictions(Model):
    """get_field_permissions() plus the tenant fields read by role. Enforcement
    uses this; the schema keeps publishing only the codenames. A model's own
    RESAAS.fields entry always wins over the tenant rule."""

    restricted = dict(get_field_permissions(Model))

    for name, role in TENANT_READ_ROLES.items():
        if name in restricted or not _is_relation(Model, name):
            continue

        restricted[name] = {"view": role, "change": None}

    return restricted


def _role_cached(request, role):
    """is_platform / is_entity_admin for this request, cached like the codenames."""

    from django_resaas.saas.core.services import group_access_service

    if request is None:
        return False

    cache = getattr(request, "_perm_cache", None)

    if cache is None:
        cache = {}
        try:
            request._perm_cache = cache
        except AttributeError:
            pass

    if role not in cache:
        try:
            cache[role] = any(
                bool(getattr(group_access_service, check)(request))
                for check in _ROLE_CHECKS[role]
            )
        except AttributeError:
            cache[role] = False

    return cache[role]


def rule_allowed(request, rule):
    """A field rule is either a permission codename or a role (role:platform,
    role:entity_admin)."""

    if rule in _ROLE_CHECKS:
        return _role_cached(request, rule)

    return has_permission_cached(request, rule)


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
        for name, perms in get_field_restrictions(Model).items()
        if not rule_allowed(request, perms["view"])
    }


def unwritable_fields(request, Model):
    """Names of the restricted fields the request may NOT write (tenant read
    rules have no write rule, so they never appear here)."""

    return {
        name
        for name, perms in get_field_restrictions(Model).items()
        if perms["change"] is not None and not rule_allowed(request, perms["change"])
    }


def is_path_readable(request, Model, path):
    """False when any step of a lookup path (amount, member__agreements__amount,
    -amount) crosses a field the request may not read."""

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

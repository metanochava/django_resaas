"""Export / import of an EntityType's profiles and their permissions (JSON) -
entity type -> template profiles (EntityTypeGroup) -> permissions.

Built on group_permissions_io_service (file reading, permission resolution,
apply_permissions with the group rules, PDF); this module only adds the
entity-type level. Platform-level operation (the actions need
change_entitytype / view_entitytype).

JSON:
    {"format": "resaas.entity_type_profiles", "version": 1,
     "entity_type": "Clinic",
     "profiles": [{"name": "Doctor",
                   "permissions": [{"app": "saude", "codename": "view_paciente"}, ...]}]}

Import (all or nothing - the whole file is validated first):
- a profile that doesn't exist is created and linked as a template of the
  EntityType; an existing one is linked if needed;
- mode "add" (default) adds the file's permissions to each listed profile;
  "replace" makes each listed profile's permissions exactly the file's.
  Profiles NOT in the file are never touched;
- never a platform profile or permission: a template is inherited by every
  Entity of the type, so a profile holding change_entitytype (e.g. Root) or
  a file granting it is refused;
- every permission added or removed must be held by the caller
  (apply_permissions / group_access_service).
"""
import json

from django.db import transaction

from django_resaas.saas.core.services import audit_service, group_access_service
from django_resaas.saas.core.services.group_permissions_io_service import (
    _bad,
    apply_permissions,
    check_mode,
    permission_rows,
    read_upload,
    resolve_permission,
)
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.group import Group

FORMAT = "resaas.entity_type_profiles"
VERSION = 1
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PROFILES = 200
MAX_NAME = 150


def template_groups(entity_type):
    return list(
        Group.objects.filter(group_entity_types__entity_type=entity_type).order_by("name").distinct()
    )


def export(entity_type):
    return {
        "format": FORMAT,
        "version": VERSION,
        "entity_type": entity_type.name,
        "profiles": [
            {"name": group.name, "permissions": permission_rows(group)}
            for group in template_groups(entity_type)
        ],
    }


def pdf_rows(entity_type):
    return [
        [group.name, row["app"], row["model"], row["codename"], row["name"]]
        for group in template_groups(entity_type)
        for row in permission_rows(group)
    ]


def _parse(upload):
    """[(name, [Permission])] or a 400 listing every problem."""
    text = read_upload(upload, max_bytes=MAX_FILE_BYTES, kind="JSON")

    try:
        data = json.loads(text)
    except ValueError:
        raise _bad("The file is not valid JSON.", "invalid_json")

    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, list):
        raise _bad("The file needs a 'profiles' list.", "profiles_missing")
    if len(profiles) > MAX_PROFILES:
        raise _bad(f"Too many profiles (maximum {MAX_PROFILES}).", "too_many_profiles")

    parsed, errors, seen = [], {}, set()

    for index, profile in enumerate(profiles):
        key = f"profiles[{index}]"
        messages = []

        name = profile.get("name") if isinstance(profile, dict) else None
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > MAX_NAME:
            errors[key] = ["Each profile needs a name (up to 150 characters)."]
            continue
        name = name.strip()
        key = f"{key} {name}"

        if name.lower() in seen:
            messages.append("This profile appears more than once.")
        seen.add(name.lower())

        existing = Group.objects.filter(name=name).first()
        if existing and existing.permissions.filter(codename=group_access_service.PLATFORM_PERMISSION).exists():
            messages.append("A platform profile cannot be an entity type profile.")

        permissions = []
        for item in profile.get("permissions") or []:
            if isinstance(item, str):
                codename, app = item, ""
            elif isinstance(item, dict):
                codename, app = str(item.get("codename") or ""), str(item.get("app") or "")
            else:
                codename, app = "", ""
            codename = codename.strip()
            if not codename:
                messages.append("A permission has no codename.")
                continue
            if codename == group_access_service.PLATFORM_PERMISSION:
                messages.append(f"'{codename}' is a platform permission and cannot be in an entity type profile.")
                continue
            permission, error = resolve_permission(codename, app.strip())
            if error:
                messages.append(error)
            else:
                permissions.append(permission)

        if messages:
            errors[key] = messages
        else:
            parsed.append((name, permissions))

    if errors:
        raise _bad("Some profiles are not valid. Nothing was changed.", "invalid_profiles",
                   details={"profiles": errors})
    return parsed


@transaction.atomic
def import_json(request, entity_type, upload, mode="add"):
    check_mode(mode)
    parsed = _parse(upload)

    results = []
    for name, permissions in parsed:
        group, created = Group.objects.get_or_create(name=name)
        EntityTypeGroup.objects.get_or_create(
            entity_type=entity_type, group=group, defaults={"state": "Active"},
        )
        summary = apply_permissions(request, group, permissions, mode)
        results.append({"name": name, "created": created, **{k: summary[k] for k in ("added", "removed", "total")}})

    audit_service.record(action="ENTITY_TYPE_PROFILES_IMPORTED", target=entity_type, actor=request.user,
                         request=request, entity_id=getattr(request, "entity_id", None))

    return {
        "mode": mode,
        "created": sum(1 for r in results if r["created"]),
        "profiles": results,
    }

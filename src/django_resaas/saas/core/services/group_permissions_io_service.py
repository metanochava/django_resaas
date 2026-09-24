"""Export / import of a group's permissions (auth/groups/{id}/...).

CSV columns: app, model, codename, name (UTF-8 with BOM, so spreadsheets
open it correctly). The same file can be edited and uploaded back.

Import rules - the same as setGroupPermissions (group_access_service):
- the group must be changeable by the caller (belongs to the Entity,
  editable, not shared) unless platform level;
- every permission ADDED or REMOVED must be held by the caller's active
  profile (no privilege escalation by delegation);
- the file is validated first: any unknown or ambiguous row -> 400 with the
  rows in error, and NOTHING changes (all or nothing);
- mode "add" (default) only adds; "replace" makes the group's permissions
  exactly the file's.
"""
import csv
import io

from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import F
from rest_framework import status

from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.services import audit_service, group_access_service
from django_resaas.saas.models.group import Group

COLUMNS = ("app", "model", "codename", "name")
MAX_FILE_BYTES = 1024 * 1024
MAX_ROWS = 5000
MODES = ("add", "replace")

# a cell starting with one of these is a formula in a spreadsheet (CSV
# injection) - exported values are prefixed with a quote
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def permission_rows(group):
    return list(
        group.permissions.annotate(
            app=F("content_type__app_label"), model=F("content_type__model"),
        )
        .order_by("content_type__app_label", "content_type__model", "codename")
        .values("app", "model", "codename", "name")
    )


def _safe_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def to_csv(group):
    buffer = io.StringIO()
    buffer.write("﻿")
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    for row in permission_rows(group):
        writer.writerow([_safe_cell(row[column]) for column in COLUMNS])
    return buffer.getvalue()


def _bad(message, code, details=None):
    return ResaasAPIException(message, code=code, details=details, status_code=status.HTTP_400_BAD_REQUEST)


# ============================================================
# Reusable pieces (also used by entity_type_profiles_io_service)
# ============================================================

def read_upload(upload, *, max_bytes=MAX_FILE_BYTES, kind="CSV"):
    """The uploaded file as text (UTF-8, BOM tolerated) or a 400."""
    if upload is None:
        raise _bad(f"Choose a {kind} file.", "file_required")
    if upload.size > max_bytes:
        raise _bad(f"The file is too large (maximum {max_bytes // (1024 * 1024)} MB).", "file_too_large")
    try:
        return upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise _bad(f"The file must be UTF-8 {kind}.", "invalid_encoding")


def check_mode(mode):
    if mode not in MODES:
        raise _bad("Invalid import mode.", "invalid_mode", details={"mode": [f"Use one of: {', '.join(MODES)}."]})
    return mode


def resolve_permission(codename, app=""):
    """(Permission, None) or (None, error message). `app` disambiguates a
    codename that exists in several apps."""
    candidates = Permission.objects.filter(codename=codename)
    if app:
        candidates = candidates.filter(content_type__app_label=app)
    found = list(candidates[:2])
    if not found:
        return None, f"Unknown permission '{codename}'."
    if len(found) > 1:
        return None, f"'{codename}' exists in several apps: fill the 'app' column."
    return found[0], None


def apply_permissions(request, group, permissions, mode):
    """Sets `permissions` on `group` (add | replace) under the group rules:
    changeable group (group_access_service) + no grant/revoke of what the
    caller doesn't hold. Call inside a transaction."""
    group_access_service.check_group_changeable(request, group)

    group = Group.objects.select_for_update().get(pk=group.pk)
    current = set(group.permissions.all())
    target = set(permissions) if mode == "replace" else current | set(permissions)

    added, removed = target - current, current - target
    group_access_service.check_delegation(request, added | removed)

    if added:
        group.permissions.add(*added)
    if removed:
        group.permissions.remove(*removed)

    return {
        "mode": mode,
        "added": len(added),
        "removed": len(removed),
        "unchanged": len(current & target),
        "total": len(target),
    }


def render_list_pdf(view, request, *, title, section_title, fields, rows):
    """The generic list PDF (django_resaas/pdf/list.html) with the Entity's
    branding (BaseAPIView helpers). fields: [(name, label)]."""
    from django.utils import timezone

    from django_resaas.saas.core.base.views import BaseAPIView
    from django_resaas.saas.core.utils import PDF
    from django_resaas.saas.core.utils.translate import Translate

    entity = BaseAPIView.get_request_entity(view, request)
    now = timezone.now()

    return PDF(
        "django_resaas/pdf/list.html",
        request,
        pdf_fields=[{"name": name, "label": Translate.tdc(request, label)} for name, label in fields],
        pdf_rows=rows,
        entity=entity,
        logo_b64=BaseAPIView.get_logo_b64(view, entity),
        data_emissao=now.date(),
        title=title,
        section_title=section_title,
        pdf_title=title,
        pdf_author=entity.name if entity else "RESAAS",
        pdf_subject=title,
        pdf_keywords="permissions, RESAAS",
        pdf_created=now.isoformat(),
        pdf_modified=now.isoformat(),
        pdf_generator="RESAAS / WeasyPrint",
    )


# ============================================================
# Group - CSV
# ============================================================

def parse_csv(upload):
    """[(line, Permission)] or 400 with every row in error."""

    text = read_upload(upload, kind="CSV")

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    if "codename" not in headers:
        raise _bad("The file needs a 'codename' column.", "codename_column_missing")
    reader.fieldnames = headers

    resolved, errors = [], {}
    for line, row in enumerate(reader, start=2):
        if line - 1 > MAX_ROWS:
            raise _bad(f"Too many rows (maximum {MAX_ROWS}).", "too_many_rows")

        codename = (row.get("codename") or "").strip()
        if not codename:
            continue  # blank line

        permission, error = resolve_permission(codename, (row.get("app") or "").strip())
        if error:
            errors[str(line)] = [error]
        else:
            resolved.append((line, permission))

    if errors:
        raise _bad("Some rows are not valid. Nothing was changed.", "invalid_rows", details={"rows": errors})

    return resolved


@transaction.atomic
def import_csv(request, group, upload, mode="add"):
    check_mode(mode)
    group_access_service.check_group_changeable(request, group)
    rows = parse_csv(upload)

    summary = apply_permissions(request, group, [permission for _, permission in rows], mode)

    audit_service.record(action="GROUP_PERMISSIONS_IMPORTED", target=group, actor=request.user,
                         request=request, entity_id=getattr(request, "entity_id", None))
    return summary

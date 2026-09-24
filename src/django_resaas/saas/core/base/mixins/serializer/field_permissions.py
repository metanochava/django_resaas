from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status

from django_resaas.saas.core.base.field_access import (
    get_field_permissions,
    unreadable_fields,
    unwritable_fields,
)
from django_resaas.saas.core.exceptions import ResaasAPIException


class FieldPermissionsMixin:
    """Field-level authorization for BaseSerializer (see core/base/field_access.py).

    Per restricted field, for the current request:
    - cannot read and cannot write -> removed from the serializer;
    - cannot read, can write       -> write_only (accepted, never returned);
    - can read, cannot write       -> read_only (returned, never accepted).

    A payload that tries to CHANGE a field the caller may not write is rejected
    with 403 (field_permission_denied), never silently dropped - so is a create
    that needs a required restricted field the caller cannot provide. Re-sending
    the value the record already holds (a whole-form PATCH) is not a change.
    """

    def get_fields(self):
        fields = super().get_fields()

        # {field_name: was_required} for the restricted fields this request may not write
        self._write_denied_fields = {}
        # restricted fields this request may not read (stripped again in to_representation)
        self._read_denied_fields = set()

        model = getattr(getattr(self, "Meta", None), "model", None)

        if model is None or not get_field_permissions(model):
            return fields

        request = self.context.get("request")
        cannot_read = unreadable_fields(request, model)
        cannot_write = unwritable_fields(request, model)

        for name in list(fields):
            field = fields[name]
            source = getattr(field, "source", None) or name

            if name not in cannot_read | cannot_write and source not in cannot_read | cannot_write:
                continue

            readable = name not in cannot_read and source not in cannot_read
            writable = name not in cannot_write and source not in cannot_write

            if not writable and not field.read_only:
                self._write_denied_fields[name] = bool(field.required)

            if not readable:
                self._read_denied_fields.add(name)

            if not readable and not writable:
                fields.pop(name)
            elif not readable:
                field.write_only = True
            elif not writable:
                field.read_only = True

        return fields

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # RepresentationMixin rebuilds FK/choice/file values from the model
        # for every name in self.fields, write_only ones included - make sure
        # an unreadable field (and its FK "<name>_id" alias) never comes back
        for name in getattr(self, "_read_denied_fields", ()):
            data.pop(name, None)
            data.pop(f"{name}_id", None)

        return data

    def to_internal_value(self, data):
        # self.fields runs get_fields() for this request
        self.fields  # noqa: B018

        denied = getattr(self, "_write_denied_fields", {})

        if denied:
            sent = sorted(
                name for name in denied
                if hasattr(data, "get") and name in data
                and not self._is_unchanged(name, data.get(name))
            )
            missing_required = sorted(
                name for name, required in denied.items()
                if required and self.instance is None and not self.partial and name not in sent
            )

            blocked = sent or missing_required

            if blocked:
                raise ResaasAPIException(
                    "You are not allowed to change these fields.",
                    code="field_permission_denied",
                    details={"fields": blocked},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        return super().to_internal_value(data)

    def _is_unchanged(self, name, value):
        """True when an update re-sends the value the record already holds -
        a whole-form PATCH (BaseStore sends the loaded record back) is not an
        attempt to change a field the caller may only read."""

        if self.instance is None or isinstance(self.instance, (list, tuple)):
            return False

        model = self.Meta.model

        try:
            model_field = model._meta.get_field(name)
        except FieldDoesNotExist:
            return False

        if model_field.many_to_many:
            return False

        # a relation may come back as the READ shape {id, value, label}
        if isinstance(value, dict):
            value = value.get("id", value.get("value"))

        try:
            if model_field.is_relation:
                current = getattr(self.instance, model_field.attname, None)
                incoming = model_field.target_field.to_python(value) if value not in (None, "") else None
            else:
                current = getattr(self.instance, model_field.attname, None)
                incoming = model_field.to_python(value) if value != "" else None
        except (DjangoValidationError, TypeError, ValueError):
            return False

        return incoming == current

import os
from django.db import models
from rest_framework import serializers
from django_resaas.core.utils.full_path import FullPath


class DynamicFieldsMixin:
    def get_fields(self):
        fields = super().get_fields()

        include = self.context.get("include_fields")
        exclude = self.context.get("exclude_fields", [])

        if include:
            fields = {k: v for k, v in fields.items() if k in include}

        for field in exclude:
            fields.pop(field, None)

        return fields


class BaseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Base serializer:
    - dynamic fields
    - file protection
    - label/value support
    """

    label_field = None
    value_field = "id"
    permanent_fields_files = []

    # 🔹 utils

    def _get_attr(self, obj, path):
        for attr in path.split("."):
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    def _file_representation(self, request, file, field_name):
        if not file:
            return None

        try:
            url = FullPath.url(
                request,
                file.url,
                temporary=field_name not in self.permanent_fields_files
            )

            name = os.path.basename(file.name)
            ext = os.path.splitext(name)[1].lstrip('.').lower()

            return {
                "url": url,
                "name": name,
                "ext": ext,
                "size": getattr(file, "size", None),
            }
        except Exception:
            return None

    # 🔹 core

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        # 🔥 label/value (simples)
        if self.label_field:
            data["label"] = self._get_attr(instance, self.label_field)
            data["value"] = getattr(instance, self.value_field, None)

        if not request:
            return data

        # 🔥 files
        for field in instance._meta.fields:
            if isinstance(field, (models.FileField, models.ImageField)):
                file = getattr(instance, field.name)
                data[field.name] = self._file_representation(request, file, field.name )

        return data
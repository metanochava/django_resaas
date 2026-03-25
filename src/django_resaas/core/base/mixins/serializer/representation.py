from django.db import models


class RepresentationMixin:
    """
    Centraliza o to_representation:
    - label/value
    - file fields
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        # 🔥 LABEL / VALUE
        if getattr(self, "label_field", None):
            data["label"] = self._get_attr(instance, self.label_field)
            data["value"] = getattr(instance, self.value_field, None)

        if not request:
            return data

        # 🔥 FILE FIELDS
        for field in instance._meta.fields:
            if isinstance(field, (models.FileField, models.ImageField)):
                file = getattr(instance, field.name)
                data[field.name] = self._file_representation(
                    request, file, field.name
                )

        return data
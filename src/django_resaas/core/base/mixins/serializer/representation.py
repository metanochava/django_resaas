from django.db import models


class RepresentationMixin:

    """
    Centraliza o to_representation:
    - label/value (via model)
    - file fields
    - foreign key → label/value automático
    - many to many → lista label/value
    - choices → label/value automático
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        # 🔥 LABEL / VALUE (via model)
        if hasattr(instance, "get_label") and hasattr(instance, "get_value"):
            data["label"] = instance.get_label()
            data["value"] = instance.get_value()

        # 🔥 CAMPOS DIRETOS
        for field in instance._meta.fields:
            value = getattr(instance, field.name, None)

            # 🔥 FILE FIELDS
            if isinstance(field, (models.FileField, models.ImageField)):
                data[field.name] = self._file_representation(
                    request, value, field.name
                )
                continue

            # 🔥 CHOICES
            if field.choices:
                display_method = f"get_{field.name}_display"

                if hasattr(instance, display_method):
                    data[field.name] = {
                        "value": value,
                        "label": getattr(instance, display_method)()
                    }
                continue

            # 🔥 FK + OneToOne
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                if value and hasattr(value, "get_label"):
                    data[field.name] = {
                        "label": value.get_label(),
                        "value": value.get_value(),
                    }
                else:
                    data[field.name] = None

        # 🔥 MANY TO MANY
        for field in instance._meta.many_to_many:
            manager = getattr(instance, field.name)

            data[field.name] = [
                {
                    "label": obj.get_label(),
                    "value": obj.get_value()
                }
                for obj in manager.all()
                if hasattr(obj, "get_label")
            ]

        return data
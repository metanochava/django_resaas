from django.db import models


class RepresentationMixin:

    """
    Centraliza o to_representation:

    ✅ label/value (via model)
    ✅ file fields
    ✅ foreign key → id + label + value
    ✅ many to many → lista id + label + value
    ✅ choices → id + label + value
    ✅ mantém <field>_id para compatibilidade
    """

    # ----------------------------
    # 🔥 HELPERS
    # ----------------------------
    def _get_label(self, obj):
        return obj.get_label() if hasattr(obj, "get_label") else str(obj)

    def _get_value(self, obj):
        return obj.get_value() if hasattr(obj, "get_value") else obj.pk

    # ----------------------------
    # 🔥 MAIN
    # ----------------------------
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        # 🔥 LABEL / VALUE (ROOT)
        if hasattr(instance, "get_label") and hasattr(instance, "get_value"):
            data["label"] = instance.get_label()
            data["value"] = instance.get_value()

        # ----------------------------
        # 🔥 CAMPOS DIRETOS
        # ----------------------------
        for field in instance._meta.fields:
            if field.name not in self.fields:
                continue

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
                        "id": value,
                        "value": value,
                        "label": getattr(instance, display_method)()
                    }
                continue

            # 🔥 FK + OneToOne (MELHORADO)
            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                if value:
                    data[field.name] = {
                        "id": value.pk,
                        "value": self._get_value(value),
                        "label": self._get_label(value),
                    }

                    # 🔥 mantém compatibilidade DRF
                    data[f"{field.name}_id"] = value.pk
                else:
                    data[field.name] = None
                    data[f"{field.name}_id"] = None

        # ----------------------------
        # 🔥 MANY TO MANY (MELHORADO)
        # ----------------------------
        for field in instance._meta.many_to_many:
            if field.name not in self.fields:
                continue

            manager = getattr(instance, field.name)

            data[field.name] = [
                {
                    "id": obj.pk,
                    "value": self._get_value(obj),
                    "label": self._get_label(obj),
                }
                for obj in manager.all()
            ]

        return data
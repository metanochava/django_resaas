from typing import Any


LABEL_KEYS = (
    "nome", "name", "title", "titulo", "descricao", "description", "label",
    "codigo", "code", "numero", "number", "username", "email"
)


class LabelValueMixin:

    class RESAAS:
        label_field = None
        value_field = "id"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._resaas = getattr(cls, "RESAAS", None)

    def _get_attr(self, path):
        obj = self
        for attr in path.split("."):
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    def get_label(self):
        resaas = getattr(self.__class__, "_resaas", None)

        label_field = getattr(resaas, "label_field", None)

        if label_field:
            val = self._get_attr(label_field)
            if val not in (None, ""):
                return str(val)

        for key in LABEL_KEYS:
            if hasattr(self, key):
                val = getattr(self, key, None)
                if val not in (None, ""):
                    return str(val)

        if hasattr(self, "id") and self.id:
            return f"{self.__class__.__name__} {self.id}"

        return self.__class__.__name__

    def get_value(self):
        resaas = getattr(self.__class__, "_resaas", None)

        value_field = getattr(resaas, "value_field", "id")

        if value_field:
            val = self._get_attr(value_field)
            if val is not None:
                return val

        return getattr(self, "id", None)

    def __str__(self):
        return self.get_label()
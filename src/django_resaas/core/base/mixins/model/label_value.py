from typing import Any
import re


LABEL_KEYS = (
    # 🔤 Nome / identificação
    "nome", "name", "title", "titulo", "label",
    "apelido", "nickname", "alias",

    # 🧾 Descrição
    "descricao", "description", "resumo", "summary", "detalhes", "details",

    # 🔢 Códigos / números
    "codigo", "code", "numero", "number", "reference", "ref",

    # 👤 User / pessoa
    "username", "email", "first_name", "last_name",
    "nome_completo", "full_name", "display_name",

    # 📞 Contacto
    "telefone", "phone", "mobile", "celular", "contact", "contacto",

    # 📍 Localização
    "endereco", "address", "cidade", "city", "pais", "country",

    # 🏢 Organização
    "empresa", "company", "organizacao", "organization",
    "entidade", "entity", "sucursal", "branch",

    # 📅 Datas
    "data", "date", "created_at", "updated_at",

    # ⚙️ Estado
    "estado", "status", "ativo", "active", "enabled", "disabled",

    # 🔐 Permissões / sistema
    "role", "perfil", "group", "grupo", "permission", "permissao"
)


class LabelValueMixin:

    class RESAAS:
        label_field = None
        value_field = "id"
        crud = True
        routes= {}

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

    
    def get_label_field(self):
        resaas = getattr(self.__class__, "_resaas", None)
        label_field = getattr(resaas, "label_field", None)

        if label_field:
           return [f for f in re.split(r"[ ,|]+", label_field) if f]
        else:
            return [] 


    def get_label(self):
        resaas = getattr(self.__class__, "_resaas", None)
        label_field = getattr(resaas, "label_field", None)

        if label_field:
            fields = [f for f in re.split(r"[ ,|]+", label_field) if f]

            values = []

            for field in fields:
                values.append(str(self._get_attr(field)))

            if values:
                return " ".join(values) 

        # 🔥 fallback inteligente
        for key in LABEL_KEYS:
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
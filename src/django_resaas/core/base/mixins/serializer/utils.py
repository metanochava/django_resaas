class SerializerUtilsMixin:

    def _get_attr(self, obj, path):
        """
        Suporta nested: "pessoa.nome"
        """
        for attr in path.split("."):
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj



class SerializerUtilsMixin:

    def _get_attr(self, obj, path, default=None):
        """
        Suporta nested: "pessoa.nome"
        """
        for attr in path.split("."):
            if obj is None:
                return default

            obj = getattr(obj, attr, default)

        return obj
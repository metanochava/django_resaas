


class SerializerUtilsMixin:

    def _get_attr(self, obj, path, default=None):
        """
        Suporta nested: "person.name"
        """
        for attr in path.split("."):
            if obj is None:
                return default

            obj = getattr(obj, attr, default)

        return obj
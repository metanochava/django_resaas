class DynamicFieldsMixin:

    def get_fields(self):
        fields = super().get_fields()

        include = self.context.get("include_fields")
        exclude = self.context.get("exclude_fields", [])

        # 🔹 normalização (query params)
        if isinstance(include, str):
            include = include.split(",")

        if isinstance(exclude, str):
            exclude = exclude.split(",")

        # 🔹 validação
        if include:
            valid_fields = set(fields.keys())
            include = [f for f in include if f in valid_fields]

            fields = {k: v for k, v in fields.items() if k in include}

        # 🔹 exclude
        for field in exclude:
            fields.pop(field, None)

        return fields
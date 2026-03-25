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
def build_select_data(queryset, request=None, preview=None):
    """{label, value, id} rows for a select. `preview` is the related model's
    normalized RESAAS.preview (see relation_preview.py); when given, every row
    also carries `preview` - the bounded display data of a relation picker."""
    if preview:
        from django_resaas.saas.core.utils.relation_preview import build_preview_item

    data = []

    for obj in queryset:
        if hasattr(obj, "get_label") and hasattr(obj, "get_value"):
            row = {
                "label": obj.get_label(),
                "value": obj.get_value()
            }
        else:
            row = {
                "label": str(obj),
                "value": getattr(obj, "id", None)
            }

        row["id"] = getattr(obj, "pk", None)

        if preview:
            row["preview"] = build_preview_item(obj, preview, request)

        data.append(row)

    return data

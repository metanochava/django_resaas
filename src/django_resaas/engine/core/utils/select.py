def build_select_data(queryset):
    data = []

    for obj in queryset:
        if hasattr(obj, "get_label") and hasattr(obj, "get_value"):
            data.append({
                "label": obj.get_label(),
                "value": obj.get_value()
            })
        else:
            data.append({
                "label": str(obj),
                "value": getattr(obj, "id", None)
            })

    return data
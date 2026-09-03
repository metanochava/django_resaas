

def reorder_fields(fields, start_fields, end_fields):
    field_map = {f['name']: f for f in fields}

    start = [field_map[name] for name in start_fields if name in field_map]

    end = [field_map[name] for name in end_fields if name in field_map]

    middle = [
        f for f in fields
        if f['name'] not in start_fields and f['name'] not in end_fields
    ]

    return [
        *start,
        *middle,
        *end
    ]
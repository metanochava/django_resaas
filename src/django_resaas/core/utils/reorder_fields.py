
def reorder_fields(fields, start_fields, end_fields):
    start = []
    middle = []
    end = []

    for f in fields:
        name = f.get('name')

        if name in start_fields:
            start.append(f)
        elif name in end_fields:
            end.append(f)
        else:
            middle.append(f)

    return [
        *start,
        *middle,
        *end
    ]

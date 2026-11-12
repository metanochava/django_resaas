"""Layered form configuration: PLATFORM -> ENTITY TYPE -> ENTITY -> BRANCH.

merge(layers) folds the definitions of one key, most general first. A lower
(more specific) layer customises what it inherits, never weakens it:

- it may add sections and fields, and change a field's label, help,
  placeholder, cols, order, default, options, component and relation, and the
  definition's title, layout and autosave;
- `required` stays true once a higher layer made it true (required = any
  layer), a higher `required_if` is kept (a lower one is added with "any"),
  and validators accumulate (a lower layer only adds rules);
- a field that is required or `locked` above cannot be hidden, made readonly
  or disabled below (its visible_if / readonly_if / disabled_if are ignored);
- mode, source and submit (the endpoint a workflow posts to) come from the
  highest layer that sets them and never change below: a lower layer cannot
  redirect where data goes.

Nothing is removed by a lower layer.
"""
import copy

OVERRIDABLE = ("label", "help", "placeholder", "cols", "order", "default", "options", "component", "relation",
               "accept", "multiple", "min_items", "max_items")
FIXED_TOP = ("mode", "source", "submit", "schema_version", "key")
CUSTOMISABLE_TOP = ("title", "layout", "autosave")


def _merge_field(base, extra):
    merged = copy.deepcopy(base)
    protected = bool(base.get("required") or base.get("locked"))
    for key in OVERRIDABLE:
        if key in extra:
            merged[key] = copy.deepcopy(extra[key])
    merged["required"] = bool(base.get("required") or extra.get("required"))
    if "required_if" in extra:
        merged["required_if"] = (
            {"any": [base["required_if"], extra["required_if"]]} if "required_if" in base else extra["required_if"]
        )
    merged["validators"] = list(base.get("validators") or []) + list(extra.get("validators") or [])
    if not merged["validators"]:
        merged.pop("validators")
    if not protected:
        for key in ("visible_if", "readonly_if", "disabled_if"):
            if key in extra:
                merged[key] = copy.deepcopy(extra[key])
    merged["locked"] = bool(base.get("locked") or extra.get("locked"))
    if not merged["locked"]:
        merged.pop("locked")
    if base.get("type") in ("repeater", "object") and extra.get("fields"):
        merged["fields"] = _merge_fields(base.get("fields") or [], extra["fields"])
    return merged


def _merge_fields(base_fields, extra_fields):
    result = [copy.deepcopy(f) for f in base_fields]
    index = {f["name"]: i for i, f in enumerate(result)}
    for field in extra_fields:
        if field["name"] in index:
            result[index[field["name"]]] = _merge_field(result[index[field["name"]]], field)
        else:
            index[field["name"]] = len(result)
            result.append(copy.deepcopy(field))
    return sorted(result, key=lambda f: f.get("order", 0)) if any("order" in f for f in result) else result


def merge(layers):
    """One definition from [platform, entity_type, entity, branch] (Nones
    skipped), most general first."""
    layers = [layer for layer in layers if layer]
    if not layers:
        return None
    merged = copy.deepcopy(layers[0])
    for layer in layers[1:]:
        for key in FIXED_TOP:
            if key not in merged and key in layer:
                merged[key] = copy.deepcopy(layer[key])
        for key in CUSTOMISABLE_TOP:
            if key in layer:
                merged[key] = copy.deepcopy(layer[key])
        sections = merged.setdefault("sections", [])
        by_key = {s["key"]: s for s in sections}
        for section in layer.get("sections") or []:
            if section["key"] in by_key:
                target = by_key[section["key"]]
                for key in ("label", "help", "layout", "cols", "order", "icon"):
                    if key in section:
                        target[key] = copy.deepcopy(section[key])
                if "visible_if" in section and not any(f.get("required") or f.get("locked")
                                                       for f in target.get("fields") or []):
                    target["visible_if"] = copy.deepcopy(section["visible_if"])
                target["fields"] = _merge_fields(target.get("fields") or [], section.get("fields") or [])
            else:
                copied = copy.deepcopy(section)
                sections.append(copied)
                by_key[copied["key"]] = copied
        if any("order" in s for s in sections):
            sections.sort(key=lambda s: s.get("order", 0))
    return merged

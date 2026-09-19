"""
Relation preview metadata: how a RELATED model wants to be shown when it is
picked through a relation field (search results and the selected card).

Declared once on the related model, next to label_field/search_fields:

    class RESAAS:
        label_field = "full_name"
        search_fields = ["name", "email", "phone"]
        preview = {
            "title": "full_name",           # optional - defaults to get_label()
            "subtitle": ["email", "phone"],  # short secondary lines
            "avatar": "photo",               # an Image/FileField
            "meta": ["date_of_birth", "nationality"],
        }

A model without `preview` keeps the lightweight label-only select, so every
existing relation behaves exactly as before. Field paths may cross ForeignKeys
with "__" (e.g. "person__email"); only real, concrete model fields are kept -
anything else is dropped rather than guessed. The schema publishes this same
normalized config (relation_config.preview) and the select endpoint
(?select=true&preview=true) returns the matching values, so the frontend never
needs model-specific knowledge.
"""
import logging

from django.core.exceptions import FieldDoesNotExist
from django.db import models

from django_resaas.saas.core.base.mixins.serializer.file_fields import FileFieldsMixin

logger = logging.getLogger(__name__)

_LIST_KEYS = ("subtitle", "meta")
_FILE_FIELDS = (models.FileField, models.ImageField)


def _resolve_field(Model, path):
    """Returns the concrete field a "a__b" path ends on, or None."""
    current = Model
    field = None

    for index, part in enumerate(str(path).split("__")):
        try:
            field = current._meta.get_field(part)
        except FieldDoesNotExist:
            return None

        if not getattr(field, "concrete", False):
            return None

        if index < len(str(path).split("__")) - 1:
            if not field.is_relation or field.related_model is None:
                return None
            current = field.related_model

    return field


def _valid(Model, path):
    return bool(path) and isinstance(path, str) and _resolve_field(Model, path) is not None


def get_relation_preview_config(Model):
    """Normalized RESAAS.preview of `Model`, or None when it declares none."""
    resaas = getattr(Model, "RESAAS", None)
    raw = getattr(resaas, "preview", None)

    if not isinstance(raw, dict) or not raw:
        return None

    config = {"title": None, "subtitle": [], "avatar": None, "meta": []}

    title = raw.get("title")
    if title:
        if _valid(Model, title):
            config["title"] = title
        else:
            logger.warning("%s.RESAAS.preview.title %r is not a model field", Model.__name__, title)

    avatar = raw.get("avatar")
    if avatar:
        field = _resolve_field(Model, avatar)
        if isinstance(field, _FILE_FIELDS):
            config["avatar"] = avatar
        else:
            logger.warning("%s.RESAAS.preview.avatar %r is not a file field", Model.__name__, avatar)

    for key in _LIST_KEYS:
        for path in raw.get(key) or []:
            if _valid(Model, path):
                config[key].append(path)
            else:
                logger.warning("%s.RESAAS.preview.%s %r is not a model field", Model.__name__, key, path)

    return config


def preview_select_related(Model, config):
    """Relations the preview reads through, so a page of results never N+1s."""
    paths = set()
    fields = [config["title"], config["avatar"], *config["subtitle"], *config["meta"]]

    for path in filter(None, fields):
        parts = path.split("__")[:-1]
        if parts:
            paths.add("__".join(parts))

    return sorted(paths)


def _read(obj, path):
    value = obj
    for part in path.split("__"):
        value = getattr(value, part, None)
        if value is None:
            return None
    return value


def _text(obj, path, field):
    value = _read(obj, path)

    if value in (None, ""):
        return None

    if field is not None and getattr(field, "choices", None):
        return str(dict(field.flatchoices).get(value, value))

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def build_preview_item(obj, config, request=None):
    """Bounded, display-only view of `obj`: only the declared fields."""
    Model = type(obj)

    title = _text(obj, config["title"], _resolve_field(Model, config["title"])) if config["title"] else None
    if not title:
        title = obj.get_label() if hasattr(obj, "get_label") else str(obj)

    avatar = None
    if config["avatar"]:
        file = _read(obj, config["avatar"])
        # the same {url, name, ext, kind, ...} representation every serializer
        # already returns for files - no second media URL system
        avatar = FileFieldsMixin()._file_representation(request, file, config["avatar"].split("__")[-1])

    subtitle = [
        text
        for text in (_text(obj, path, _resolve_field(Model, path)) for path in config["subtitle"])
        if text
    ]

    meta = []
    for path in config["meta"]:
        field = _resolve_field(Model, path)
        text = _text(obj, path, field)
        if text:
            meta.append({
                "field": path,
                "label": str(getattr(field, "verbose_name", path)).replace("_", " ").title(),
                "value": text,
            })

    return {"title": title, "subtitle": subtitle, "avatar": avatar, "meta": meta}

"""
Branding of the e-mails RESAAS sends (OTP codes, password reset, welcome):
the name, the logo and the colours of the Entity or EntityType the message
is about, so every template (templates/django_resaas/email_*.html, through
email_base.html) wears the same look as the app.

Which look, first match wins:

1. an explicit `entity` (callers that know it, e.g. bootstrap);
2. the Entity of the request's Origin (`Entity.site`, the public-site rule of
   site_service.entity_for_origin);
3. the Entity of the authenticated request (`request.entity_id`, set from the
   signed X-RESAAS-Context);
4. the EntityType of the Origin's host - first subdomain label, `www`
   skipped, compared with EntityType.name ignoring case (the same rule as the
   frontend's utils/entityTypeHost.js: saude.example.com -> Saude);
5. nothing: the templates fall back to their defaults.

An Entity uses its own Theme, else its EntityType's. Colours are taken only
when they are plain CSS colours (hex / rgb() / hsl()), because they end up
inside a style attribute of the e-mail.
"""
import re

from django_resaas.saas.core.services.site_service import entity_for_origin, site_host

_COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|(rgb|rgba|hsl|hsla)\([0-9.,%\s]+\))$")


def _color(value):
    value = str(value or "").strip()
    return value if _COLOR.match(value) else None


def _tint(color, amount=0.9):
    """A light shade of a #rrggbb colour (for the OTP code box); None otherwise."""
    if not color or not re.match(r"^#[0-9a-fA-F]{6}$", color):
        return None
    channels = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(c + (255 - c) * amount) for c in channels]
    return "#" + "".join(f"{c:02x}" for c in mixed)


def _file_url(request, field):
    if not field:
        return None
    try:
        from django_resaas.saas.core.utils.full_path import FullPath

        return FullPath.url(request, field.url, temporary=False) if request else field.url
    except ValueError:
        return None


def _entity_from_request(request):
    if request is None:
        return None
    from django_resaas.saas.models.entity import Entity

    entity = entity_for_origin(request.META.get("HTTP_ORIGIN", ""))
    if entity is None and getattr(request, "entity_id", None):
        entity = Entity.objects.filter(pk=request.entity_id).first()
    return entity


def _entity_type_from_request(request):
    if request is None:
        return None
    from django_resaas.saas.models.entity_type import EntityType

    host = site_host(request.META.get("HTTP_ORIGIN", "")).split(":")[0]
    labels = [label for label in host.split(".") if label]
    if labels and labels[0].lower() == "www":
        labels = labels[1:]
    if len(labels) < 2:
        return None
    return EntityType.objects.filter(name__iexact=labels[0]).first()


def email_brand(request=None, entity=None):
    """Template context for the branded e-mails: entity_name, logo,
    brand_color, brand_text_color, brand_tint. Missing values are None."""
    brand = {"entity_name": None, "logo": None, "brand_color": None, "brand_text_color": None, "brand_tint": None}

    entity = entity or _entity_from_request(request)
    entity_type = getattr(entity, "entity_type", None) if entity else _entity_type_from_request(request)
    theme = getattr(entity, "theme", None) or getattr(entity_type, "theme", None)

    if entity is not None:
        brand["entity_name"] = entity.name
        layout = getattr(entity, "layout_settings", None)
        if layout is None or getattr(layout, "display_logo_login", True):
            brand["logo"] = _file_url(request, getattr(entity, "logo", None))
    elif entity_type is not None:
        brand["entity_name"] = entity_type.label or entity_type.name
        brand["logo"] = _file_url(request, getattr(entity_type, "icon", None))

    if theme is not None:
        brand["brand_color"] = _color(theme.primary)
        brand["brand_text_color"] = _color(getattr(theme, "header_text", None))
        brand["brand_tint"] = _tint(brand["brand_color"])

    return brand


def resolve_email_branding(request):
    """(entity_name, logo_url) - kept for existing callers; see email_brand()."""
    brand = email_brand(request)
    return brand["entity_name"], brand["logo"]

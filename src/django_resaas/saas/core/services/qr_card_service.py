"""QR cards: the printable card of an Entity or a Branch (payment-app style:
the brand colour, the logo, a big QR code and what it opens).

What the QR code opens
- Entity: its website (Entity.site); without one, its location on Google
  Maps (Entity.google_place_id, else the first Branch with a location).
- Branch: its location on Google Maps (its main Address: latitude/longitude,
  else place_id, else the formatted address); without one, the Entity's
  website.
- Nothing of that: no QR code; the card says what to fill in.

Only http(s) websites are followed (as the frontend's safeSiteUrl). The
colour is the Entity's theme primary (else its EntityType's). Every text is
translated with the request language (Translate.tdc).
"""
import re
from urllib.parse import urlencode, urlparse

from django_resaas.saas.core.utils.bar_qr_code_64 import make_brand_qr_b64, png_bytes_to_b64
from django_resaas.saas.core.utils.translate import Translate

DEFAULT_COLOR = "#1976D2"
HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
MAPS_DIRECTIONS = "https://www.google.com/maps/dir/?"
MAPS_SEARCH = "https://www.google.com/maps/search/?"


def safe_site_url(url):
    """The website when it is an absolute http(s) URL, else None."""
    value = (url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return value
    return None


def address_map_url(address, name=""):
    """Google Maps for an Address: directions to its coordinates, else a search
    by place_id or by the formatted address. None without any of them."""
    if address is None:
        return None
    if address.latitude is not None and address.longitude is not None:
        return MAPS_DIRECTIONS + urlencode({"api": 1, "destination": f"{address.latitude},{address.longitude}"})
    if address.place_id:
        return MAPS_SEARCH + urlencode({"api": 1, "query": name or address.formatted_address or "", "query_place_id": address.place_id})
    if address.formatted_address:
        return MAPS_SEARCH + urlencode({"api": 1, "query": address.formatted_address})
    return None


def address_text(address):
    if address is None:
        return ""
    if address.formatted_address:
        return address.formatted_address
    parts = [address.route, address.street_number, address.neighborhood, address.locality, address.country]
    return ", ".join(str(p) for p in parts if p)


def entity_map_url(entity):
    if entity.google_place_id:
        return MAPS_SEARCH + urlencode({"api": 1, "query": entity.name or "", "query_place_id": entity.google_place_id})
    for branch in entity.branch_set.order_by("created_at"):
        url = address_map_url(branch.address, entity.name)
        if url:
            return url
    return None


def entity_target(entity):
    """(kind, url) the Entity's QR code opens: ("site", ...), ("map", ...) or (None, None)."""
    site = safe_site_url(entity.site)
    if site:
        return "site", site
    url = entity_map_url(entity)
    return ("map", url) if url else (None, None)


def branch_target(branch):
    """(kind, url) the Branch's QR code opens: ("map", ...), ("site", ...) or (None, None)."""
    url = address_map_url(branch.address, branch.name)
    if url:
        return "map", url
    site = safe_site_url(branch.entity.site)
    return ("site", site) if site else (None, None)


def brand_color(entity):
    """The theme primary as #rgb/#rrggbb - anything else (it goes into the
    template's CSS, where a value like "red;}@import url(...)" would make
    WeasyPrint fetch a URL) falls back to DEFAULT_COLOR."""
    theme = entity.theme or getattr(entity.entity_type, "theme", None)
    color = (getattr(theme, "primary", None) or "").strip()
    return color if HEX_COLOR.fullmatch(color) else DEFAULT_COLOR


def _read(field):
    try:
        if field and field.path:
            with open(field.path, "rb") as f:
                return f.read()
    except (FileNotFoundError, ValueError, OSError):
        pass
    return None


def card_context(request, entity, branch=None):
    """Context of django_resaas/pdf/qr_card.html for an Entity, or for one of
    its Branches when `branch` is given."""
    t = lambda text: Translate.tdc(request, text)  # noqa: E731

    kind, url = branch_target(branch) if branch else entity_target(entity)
    color = brand_color(entity)
    logo = _read(entity.logo)

    if kind == "site":
        heading = t("Scan to visit our website")
        link = urlparse(url).netloc
    elif kind == "map":
        heading = t("Scan for directions")
        link = "Google Maps"
    else:
        heading = link = ""

    return {
        "entity": entity,
        "branch": branch,
        "title": branch.name if branch else entity.name,
        "subtitle": entity.name if branch else getattr(entity.entity_type, "name", ""),
        "color": color,
        "logo_b64": png_bytes_to_b64(logo) if logo else None,
        "qr_b64": make_brand_qr_b64(url, color=color, logo_bytes=logo) if url else None,
        "target": kind,
        "url": url,
        "link": link,
        "address": address_text(branch.address) if branch else "",
        "labels": {
            "heading": heading,
            "hint": t("Point your phone's camera at the code"),
            "missing": t(
                "No website or location registered: add the Entity's website or the Branch's address to show the QR code."
            ),
            "address": t("Address"),
        },
    }

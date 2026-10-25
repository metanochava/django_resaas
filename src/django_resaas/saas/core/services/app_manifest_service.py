"""Web app manifest of an EntityType: the name, colour and icons a frontend
installed as an app (PWA) shows for that EntityType's domain
(farmacia.example.com installs as "Farmacia", with the type's icon).

Only public data of the type is used (the same as EntityTypePublicSerializer
and themeGet): its label, its icon and its theme primary colour.

start_url / scope / id are absolute URLs of the frontend, which must be the
origin the browser installs from. The origin given by the frontend is used
only when the CORS policy trusts it (CORS_ALLOWED_ORIGINS /
CORS_ALLOWED_ORIGIN_REGEXES); otherwise they are left out and the browser
falls back to the page being installed.

Icon URLs are relative to the manifest URL (browsers resolve them against
it), so they keep the API's scheme and host whatever the proxy in front.
"""
import re
from io import BytesIO

from django.conf import settings

from django_resaas.saas.core.services.qr_card_service import HEX_COLOR

ICON_SIZES = (192, 512)
APPLE_ICON_SIZE = 180
ALLOWED_ICON_SIZES = ICON_SIZES + (APPLE_ICON_SIZE,)
DEFAULT_THEME_COLOR = "#1976d2"
BACKGROUND_COLOR = "#ffffff"
SHORT_NAME_LENGTH = 12

# padding around the icon: "any" icons are shown whole; "maskable" ones may be
# cut to a circle, so the image stays inside the central 80% safe zone
PADDING = {"any": 0.08, "maskable": 0.2}


def cors_allows_origin(origin):
    """Whether the CORS policy trusts this origin (an explicit allow-list or
    regex, never CORS_ORIGIN_ALLOW_ALL)."""
    origin = (origin or "").rstrip("/")
    if not origin or getattr(settings, "CORS_ORIGIN_ALLOW_ALL", False) is True:
        return False
    allowed = [item.rstrip("/") for item in getattr(settings, "CORS_ALLOWED_ORIGINS", []) if item]
    patterns = getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", [])
    return origin in allowed or any(re.match(pattern, origin) for pattern in patterns)


def theme_color(entity_type):
    color = (getattr(entity_type.theme, "primary", None) or "").strip()
    return color if HEX_COLOR.fullmatch(color) else DEFAULT_THEME_COLOR


def has_icon(entity_type):
    try:
        return bool(entity_type.icon) and entity_type.icon.storage.exists(entity_type.icon.name)
    except (ValueError, OSError):
        return False


def manifest(entity_type, origin=None):
    """The manifest (a dict) of an EntityType's app."""
    name = entity_type.label or entity_type.name or ""
    data = {
        "name": name,
        "short_name": name[:SHORT_NAME_LENGTH],
        "display": "standalone",
        "orientation": "any",
        "background_color": BACKGROUND_COLOR,
        "theme_color": theme_color(entity_type),
        "icons": [],
    }

    if has_icon(entity_type):
        for purpose in ("any", "maskable"):
            for size in ICON_SIZES:
                data["icons"].append({
                    # relative to .../entitytypes/manifest/
                    "src": f"../{entity_type.id}/app_icon/?size={size}&purpose={purpose}",
                    "sizes": f"{size}x{size}",
                    "type": "image/png",
                    "purpose": purpose,
                })

    origin = (origin or "").rstrip("/")
    if cors_allows_origin(origin):
        data["id"] = data["start_url"] = data["scope"] = f"{origin}/"
    return data


def icon_png(entity_type, size, purpose="any"):
    """The type's icon as a square PNG of `size` on a white background, or
    None when the type has no readable image."""
    from PIL import Image

    if not has_icon(entity_type):
        return None
    try:
        with entity_type.icon.open("rb") as f:
            image = Image.open(BytesIO(f.read()))
            image.load()
    except Exception:
        return None

    image = image.convert("RGBA")
    box = image.getbbox()
    if box:
        image = image.crop(box)

    inner = int(size * (1 - 2 * PADDING.get(purpose, PADDING["any"])))
    image.thumbnail((inner, inner), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    canvas.alpha_composite(image, ((size - image.size[0]) // 2, (size - image.size[1]) // 2))

    buf = BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()

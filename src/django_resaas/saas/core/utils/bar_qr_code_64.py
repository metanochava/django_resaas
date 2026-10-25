
import base64
from io import BytesIO
from django.conf import settings
import os

import qrcode
import barcode
from barcode.writer import ImageWriter

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

def png_bytes_to_b64(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("utf-8")


def make_qr_b64(text: str) -> str:
    img = qrcode.make(text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return png_bytes_to_b64(buf.getvalue())


def _hex_to_rgb(color, default=(0, 0, 0)):
    value = (color or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return default


def make_brand_qr_b64(text: str, color: str = "#000000", logo_bytes: bytes = None) -> str:
    """A QR code for printed cards (payment-app style): rounded modules in the
    brand colour, high error correction and, when given, the logo in a white
    rounded square at the centre (H tolerates the ~20% it covers)."""
    from PIL import Image, ImageDraw
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.colormasks import SolidFillColorMask
    from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=1)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(back_color=(255, 255, 255), front_color=_hex_to_rgb(color)),
    ).convert("RGBA")

    if logo_bytes:
        try:
            logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
        except Exception:
            logo = None
        if logo is not None:
            side = img.size[0] // 4
            pad = side // 8
            badge = Image.new("RGBA", (side + 2 * pad, side + 2 * pad), (255, 255, 255, 0))
            ImageDraw.Draw(badge).rounded_rectangle(
                (0, 0, badge.size[0] - 1, badge.size[1] - 1), radius=pad * 2, fill=(255, 255, 255, 255)
            )
            logo.thumbnail((side, side))
            badge.alpha_composite(logo, ((badge.size[0] - logo.size[0]) // 2, (badge.size[1] - logo.size[1]) // 2))
            img.alpha_composite(badge, ((img.size[0] - badge.size[0]) // 2, (img.size[1] - badge.size[1]) // 2))

    buf = BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return png_bytes_to_b64(buf.getvalue())


def make_barcode_b64(value: str) -> str:
    CODE128 = barcode.get_barcode_class("code128")
    buf = BytesIO()
    CODE128(value, writer=ImageWriter()).write(buf, options={"quiet_zone": 2})
    return png_bytes_to_b64(buf.getvalue())

def PDF(template_path, request, doc=None, download=False, **context):
    doc = doc or {"name": "pdf"}
    context["request"] = request
    if template_path.split('.')[-1] =='html':
        html = render_to_string(template_path, context)
    else:
        html = template_path


    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    filename = doc.get("name", "pdf").replace(" ", "_")

    response = HttpResponse(pdf, content_type="application/pdf")

    disposition = "attachment" if download else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}.pdf"'

    return response



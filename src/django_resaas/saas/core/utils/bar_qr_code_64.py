
import base64
import re
import unicodedata
from urllib.parse import quote
from io import BytesIO
from django.conf import settings
import os

import qrcode
import barcode
from barcode.writer import ImageWriter

from django.http import HttpResponse
from django.template.loader import render_to_string
import pydyf
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

def _entity_label(request):
    """ "<EntityType> - <Entity>" of the request's tenant (the signed context's
    entity_id, never a client value): the PDF's Producer."""
    entity_id = getattr(request, "entity_id", None)
    if not entity_id:
        return None
    from django.apps import apps
    from django_resaas.saas.core.utils.translate import Translate

    Entity = apps.get_model("django_resaas", "Entity")
    entity = Entity.objects.select_related("entity_type").filter(pk=entity_id).first()
    if entity is None:
        return None
    entity_type = entity.entity_type
    type_name = (getattr(entity_type, "label", None) or getattr(entity_type, "name", None) or "").strip()
    if type_name:
        type_name = Translate.tdc(request, type_name)
    parts = [type_name, (entity.name or "").strip()]
    return " - ".join(part for part in parts if part and part != "-") or None


def _user_label(request):
    """The name of the user logged in when the PDF is produced: its Author."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    person = getattr(user, "person", None)
    name = (getattr(person, "full_name", None) or "").strip() if person else ""
    if not name and hasattr(user, "get_full_name"):
        name = (user.get_full_name() or "").strip()
    return name or getattr(user, "username", None) or getattr(user, "email", None) or None


def _file_name(title):
    """The title without spaces: "Atestado Médico - Elsa Nhaca" -> "AtestadoMédico-ElsaNhaca"."""
    text = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "", str(title or ""))
    return re.sub(r"\s+", "", text).strip(".-") or None


def _file_part(text):
    """ASCII fallback of a file name: "AtestadoMédico-ElsaNhaca" -> "AtestadoMedico-ElsaNhaca"."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_.")


def _template_subject(template_path):
    if not isinstance(template_path, str) or not template_path.endswith(".html"):
        return None
    return template_path.rsplit("/", 1)[-1][:-5].replace("_", " ").strip().title() or None


def PDF(template_path, request, doc=None, download=False, **context):
    """Render a template to a PDF response.

    Document properties come from the context (all optional):
      pdf_subject   what the document is, canonical English ("Medical Certificate"),
                    translated to the request's language
      pdf_person    who it is about ("Elsa Nhaca")
      pdf_title     overrides "<subject> - <person>"
      pdf_keywords  overrides "<subject>, <person>, <entity>, <date>"
    Producer is "<EntityType> - <Entity>"; Author is the user logged in when it
    is produced; Creator is RESAAS; the
    creation/modification dates are now. The file is named after the title
    (or doc={"name": ...}) with the spaces removed, joined to the creation
    date: "Medical Certificate - Elsa Nhaca" -> "MedicalCertificate-ElsaNhaca_2026-11-04.pdf".
    """
    from django.utils import timezone
    from django_resaas.saas.core.utils.translate import Translate

    context["request"] = request
    if template_path.split('.')[-1] == 'html':
        html = render_to_string(template_path, context)
    else:
        html = template_path

    document = HTML(string=html, base_url=request.build_absolute_uri("/")).render()
    metadata = document.metadata

    now = timezone.localtime()
    today = now.date().isoformat()
    owner = _entity_label(request)
    author = _user_label(request)
    subject = context.get("pdf_subject") or metadata.description or metadata.title or _template_subject(template_path)
    subject = Translate.tdc(request, str(subject)) if subject else None
    person = str(context.get("pdf_person") or "").strip() or None

    metadata.title = (
        context.get("pdf_title")
        or " - ".join(part for part in (subject, person) if part)
        or metadata.title
    )
    if subject:
        metadata.description = subject
    if author:
        metadata.authors = [author]
    keywords = context.get("pdf_keywords")
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    metadata.keywords = keywords or [k for k in (subject, person, owner, today) if k]
    metadata.generator = "RESAAS"
    metadata.created = metadata.modified = now.isoformat(timespec="seconds")

    def finisher(_document, pdf):
        if owner:
            pdf.info["Producer"] = pydyf.String(owner)

    pdf = document.write_pdf(finisher=finisher)

    filename = f'{_file_name((doc or {}).get("name") or metadata.title) or "document"}_{today}'

    response = HttpResponse(pdf, content_type="application/pdf")

    disposition = "attachment" if download else "inline"
    ascii_name = _file_part(filename) or "document"
    response["Content-Disposition"] = (
        f'{disposition}; filename="{ascii_name}.pdf"; '
        f"filename*=UTF-8''{quote(filename)}.pdf"
    )

    return response

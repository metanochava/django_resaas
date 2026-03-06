# utils/pdf_assets.py
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


def make_barcode_b64(value: str) -> str:
    CODE128 = barcode.get_barcode_class("code128")
    buf = BytesIO()
    CODE128(value, writer=ImageWriter()).write(buf, options={"quiet_zone": 2})
    return png_bytes_to_b64(buf.getvalue())

def PDF(template_path, request, doc=None, download=False, **context):
    doc = doc or {"name": "pdf"}

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



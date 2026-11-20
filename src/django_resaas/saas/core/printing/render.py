"""A printable document to PDF, on a paper format (formats.py), with the
existing PDF() (WeasyPrint). A thermal roll is rendered twice: once on a very
long page to measure the content, then on a page exactly that long."""
from django.template.loader import render_to_string

from django_resaas.saas.core.utils import PDF

from .formats import PAPER_FORMATS

PX_TO_MM = 25.4 / 96
MEASURE_HEIGHT_MM = 3000


def page_css(paper, height_mm=None):
    height = height_mm or paper["height"] or MEASURE_HEIGHT_MM
    return f"@page {{ size: {paper['width']}mm {height:.1f}mm; margin: {paper['margin']}mm; }}"


def branding(request):
    """The Entity and Branch of the request's context, and the Entity's logo."""
    from django_resaas.saas.core.utils import png_bytes_to_b64
    from django_resaas.saas.models.branch import Branch
    from django_resaas.saas.models.entity import Entity

    entity = Entity.objects.filter(id=getattr(request, "entity_id", None)).first()
    branch = Branch.objects.filter(id=getattr(request, "branch_id", None), entity=entity).first() if entity else None
    logo_b64 = None
    try:
        if entity and entity.logo and entity.logo.path:
            with open(entity.logo.path, "rb") as handle:
                logo_b64 = png_bytes_to_b64(handle.read())
    except Exception:
        logo_b64 = None
    return {"entity": entity, "branch": branch, "logo_b64": logo_b64}


def _context(request, document, obj, paper_code):
    from django.utils import timezone

    paper = PAPER_FORMATS[paper_code]
    context = branding(request)
    context.update(dict(document["context"](request, obj, paper) or {}))
    context.update({"paper": paper, "paper_code": paper_code, "document": document,
                    "printed_at": timezone.localtime()})
    context.update(_codes(request, document, obj))
    return context


def _codes(request, document, obj):
    """The document's QR code and barcode (its optional "qr" / "barcode"
    callables: (request, obj) -> text), as base64 PNGs for the base template.
    A code that cannot be drawn is left out, never a failed print."""
    from django_resaas.saas.core.utils import make_barcode_b64, make_qr_b64

    codes = {}
    bars_only = lambda value: make_barcode_b64(value, text=False)  # noqa: E731 - the template prints the value
    builders = dict(document)
    # a document that can be verified: its QR code is the verification link
    if document.get("verify"):
        from .verify import verify_url

        builders["qr"] = lambda request_, obj_: verify_url(request_, document["code"], obj_)
    for key, make in (("qr", make_qr_b64), ("barcode", bars_only)):
        build = builders.get(key)
        if not build:
            continue
        try:
            value = build(request, obj)
            if value:
                codes[f"{key}_b64"] = make(str(value))
                codes[f"{key}_value"] = str(value)
        except Exception:
            continue
    return codes


def content_height_mm(template, context):
    from weasyprint import HTML

    rendered = HTML(string=render_to_string(template, context)).render()
    root = rendered.pages[0]._page_box.children[0]
    return root.margin_height() * PX_TO_MM


def render_pdf(request, document, obj, paper_code, download=False):
    paper = PAPER_FORMATS[paper_code]
    context = _context(request, document, obj, paper_code)
    context["request"] = request
    height = None
    if paper["thermal"]:
        context["page_css"] = page_css(paper)
        height = content_height_mm(document["template"], context) + 2 * paper["margin"] + 2
    context["page_css"] = page_css(paper, height)
    if document.get("title"):
        context.setdefault("pdf_title", document["title"](obj))
    context.setdefault("pdf_subject", document["label"])
    context.pop("request", None)   # PDF() adds it
    return PDF(document["template"], request, download=download, **context)

import uuid

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_resaas.saas.core.base.response_mixin import ResaasResponseMixin
from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.core.exceptions import ResaasAPIException
from django_resaas.saas.core.printing import PAPER_FORMATS, registry
from django_resaas.saas.core.printing.render import render_pdf
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.data.user.views.registration_throttles import _ByAddress
from django_resaas.saas.data.printing.serializers.printing import PrinterSerializer
from django_resaas.saas.models.printer import Printer


@registerView('printers')
class PrinterAPIView(BaseAPIView):
    """The printers of the current Branch (list_/view_/add_/change_/delete_printer)."""
    serializer_class = PrinterSerializer
    queryset = Printer.objects.all()


def _require_context(request):
    if not getattr(request, "entity_id", None) or not getattr(request, "branch_id", None):
        raise ResaasAPIException("RESAAS context is required.", code="tenant_context_required", status_code=403)


def _printers(request):
    return list(Printer.objects.filter(entity_id=request.entity_id, branch_id=request.branch_id, active=True))


class PrintDocumentsAPIView(ResaasResponseMixin, APIView):
    """PROTECTED. GET printing/documents/: what the current profile may print
    here, each with its formats and this Branch's default printer, plus the
    Branch's active printers and every paper format."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_context(request)
        printers = _printers(request)
        rows = []
        for document in registry.available(request):
            default = next((p for p in printers if document["code"] in (p.documents or [])
                            and p.paper_format in document["formats"]), None)
            rows.append({
                "code": document["code"], "label": document["label"], "app": document["app"],
                "formats": document["formats"], "default_format": document["default_format"],
                "printer": ({"id": str(default.id), "name": default.name, "paper_format": default.paper_format}
                            if default else None),
            })
        return Response({
            "documents": rows,
            "printers": [{"id": str(p.id), "name": p.name, "paper_format": p.paper_format,
                          "documents": p.documents or []} for p in printers],
            "formats": [{"code": code, **{k: v for k, v in paper.items()}} for code, paper in PAPER_FORMATS.items()],
        }, status=status.HTTP_200_OK)


class PrintDocumentPDFAPIView(ResaasResponseMixin, APIView):
    """PROTECTED. GET printing/{code}/{object_id}/pdf/?paper=<format>: the
    document as a PDF. Needs the document's permission in the current
    profile; the object must be among the document's queryset for the
    request (its tenant scope) - else 404; the paper must be one of the
    document's formats (default: this Branch's printer's, else the
    document's default)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, code, object_id):
        _require_context(request)
        document = next((d for d in registry.available(request) if d["code"] == code), None)
        if document is None:
            if registry.get(code) is None:
                raise ResaasAPIException("Unknown document.", code="document_not_found", status_code=404)
            raise ResaasAPIException("Permission denied", code="permission_denied", status_code=403)

        paper = request.query_params.get("paper")
        if not paper:
            default = next((p for p in _printers(request) if code in (p.documents or [])
                            and p.paper_format in document["formats"]), None)
            paper = default.paper_format if default else document["default_format"]
        if paper not in document["formats"]:
            raise ResaasAPIException("This paper is not available for this document.",
                                     code="paper_not_available", status_code=400)

        try:
            uuid.UUID(str(object_id))
        except ValueError:
            raise ResaasAPIException("Document not found.", code="object_not_found", status_code=404)
        obj = document["queryset"](request).filter(pk=object_id).first()
        if obj is None:
            raise ResaasAPIException("Document not found.", code="object_not_found", status_code=404)

        return render_pdf(request, document, obj, paper, download=request.query_params.get("download") == "1")


# a record's estado / status that means the printed document no longer counts
VOIDED_WORDS = ("anulad", "cancelad", "cancelled", "canceled", "voided", "revoked", "revogad")


def _local_time(iso):
    """"2026-11-20T13:05+00:00" -> "2026-11-20 14:05" (the server's time zone)."""
    from datetime import datetime

    from django.utils import timezone

    try:
        return timezone.localtime(datetime.fromisoformat(str(iso))).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(iso or "")


class PrintVerifyThrottle(_ByAddress):
    scope = "print_verify"
    setting = "RESAAS_PRINT_VERIFY_THROTTLE_RATE"
    default = "60/minute"


class PrintVerifyAPIView(ResaasResponseMixin, APIView):
    """PUBLIC (PUBLIC_BY_DESIGN). GET printing/verify/<token>/: the page behind
    a printed document's QR code. The token is signed (core/printing/verify.py):
    the document and its id come from it, never from the client. Answers only
    the document's public fields (its "verify" callable) - never a customer,
    items or tax ids. An unknown token, a document that cannot be verified and
    a record that is gone all answer the same 404. Throttled per address."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PrintVerifyThrottle]

    def get(self, request, token):
        from django_resaas.saas.core.printing.verify import ISSUE, read_payload, read_token

        not_found = ResaasAPIException("This document was not issued by this system.",
                                       code="document_not_verified", status_code=404)
        payload = read_payload(token)
        if payload and payload["d"] == ISSUE:
            return self._issued(request, payload, not_found)
        found = read_token(token)
        document = registry.get(found[0]) if found else None
        if document is None or not document.get("verify") or not document.get("verify_queryset"):
            raise not_found
        obj = document["verify_queryset"]().filter(pk=found[1]).first()
        if obj is None:
            raise not_found

        entity = getattr(obj, "entity", None)
        branch = getattr(obj, "branch", None)
        public = dict(document["verify"](obj) or {})
        # "__voided__": the document no longer counts (a voided sale) - shown loud
        voided = bool(public.pop("__voided__", False))
        return Response({
            "voided": voided,
            "document": Translate.tdc(request, document["label"]),
            "entity": getattr(entity, "name", None),
            "branch": getattr(branch, "name", None),
            "issued_at": getattr(obj, "created_at", None),
            # values are translated too ("Voided" -> "Anulada"); a value with no
            # translation (a number, a name) stays as it is
            "fields": [{"label": Translate.tdc(request, label),
                        "value": Translate.tdc(request, value) if isinstance(value, str) else value}
                       for label, value in public.items()],
        }, status=status.HTTP_200_OK)

    def _issued(self, request, payload, not_found):
        """A PDF verified by its issue token (core/utils PDF()): what it is,
        who issued it and when; for one record, whether it still stands
        (gone, or its estado/status voided/cancelled). Never the record's content."""
        from django.apps import apps as django_apps
        from django_resaas.saas.models.branch import Branch
        from django_resaas.saas.models.entity import Entity

        entity = Entity.objects.filter(id=payload.get("e")).first() if payload.get("e") else None
        branch = Branch.objects.filter(id=payload.get("b"), entity=entity).first() if payload.get("b") and entity else None
        voided = False
        if payload.get("m") and payload.get("o"):
            try:
                model = django_apps.get_model(payload["m"])
            except (LookupError, ValueError):
                raise not_found
            manager = getattr(model, "all_objects", None) or model._default_manager
            obj = manager.filter(pk=payload["o"]).first()
            if obj is not None and entity is not None and getattr(obj, "entity_id", entity.id) != entity.id:
                raise not_found
            # gone (deleted / soft-deleted), or its business status says so;
            # TimeModel.state is no signal ("Inactive" is its default)
            deleted = obj is None or getattr(obj, "deleted_at", None) is not None
            status_value = " ".join(str(getattr(obj, name, "") or "") for name in ("estado", "status")).lower() if obj is not None else ""
            voided = deleted or any(word in status_value for word in VOIDED_WORDS)
        t = lambda text: Translate.tdc(request, text)  # noqa: E731
        fields = [{"label": t("Issued on"), "value": _local_time(payload.get("t"))}]
        if payload.get("m"):
            fields.append({"label": t("Status"), "value": t("No longer valid") if voided else t("Valid")})
        return Response({
            "voided": voided,
            "document": t(payload.get("s") or "Document"),
            "entity": getattr(entity, "name", None),
            "branch": getattr(branch, "name", None),
            "issued_at": payload.get("t"),
            "fields": fields,
        }, status=status.HTTP_200_OK)

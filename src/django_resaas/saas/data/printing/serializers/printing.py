from django.db import transaction
from rest_framework import serializers

from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.core.printing import registry
from django_resaas.saas.models.printer import Printer


class PrinterSerializer(BaseSerializer):
    """`documents`: registered document codes that support this printer's
    paper. A document a printer takes as default is dropped from the other
    printers of the same Branch (one default per document and Branch)."""

    class Meta:
        model = Printer
        fields = "__all__"
        read_only_fields = ["entity", "branch"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        codes = attrs.get("documents", getattr(self.instance, "documents", None)) or []
        paper = attrs.get("paper_format", getattr(self.instance, "paper_format", None))
        if not isinstance(codes, list):
            raise serializers.ValidationError({"documents": ["A list of document codes is required."]})
        errors = []
        for code in codes:
            document = registry.get(code)
            if document is None:
                errors.append(f"Unknown document: {code}")
            elif paper not in document["formats"]:
                errors.append(f"{code} cannot be printed on {paper}")
        if errors:
            raise serializers.ValidationError({"documents": errors})
        attrs["documents"] = list(dict.fromkeys(codes))
        return attrs

    def save(self, **kwargs):
        with transaction.atomic():
            printer = super().save(**kwargs)
            codes = set(printer.documents or [])
            if codes:
                others = (Printer.objects.select_for_update()
                          .filter(entity_id=printer.entity_id, branch_id=printer.branch_id)
                          .exclude(pk=printer.pk))
                for other in others:
                    kept = [code for code in (other.documents or []) if code not in codes]
                    if kept != list(other.documents or []):
                        other.documents = kept
                        other.save(update_fields=["documents", "updated_at"])
        return printer

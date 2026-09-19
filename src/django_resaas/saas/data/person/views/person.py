
# =========================
# Django REST Framework
# =========================
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from django_resaas.saas.models.person import Person
from django_resaas.saas.models.document import Document
from django_resaas.saas.models.document import DocumentType
from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.core.decorators.action import resaas_action
from django_resaas.saas.core.base.permissions import isPermited
from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.core.services.person_matching_service import find_candidates
from django_resaas.saas.core.utils.api_response import all as all_response

from django_resaas.saas.data.person.serializers.person import PersonSerializer
from django_resaas.saas.data.document.serializers.document import DocumentSerializer

@registerView('persons')
class  PersonAPIView(BaseAPIView):
    serializer_class = PersonSerializer
    queryset = Person.objects.all()
    lookup_field = "id"

    # ======================================================
    # POST /api/django_resaas/persons/match/
    # Centralised duplicate-detection (person_matching_service) - see
    # its own docstring for why this lives outside any one business
    # module (add_employee today, future Patient/Student/Customer
    # intake). Read-only: never creates/merges/blocks anything itself,
    # just reports candidates and WHY each one matched.
    # ======================================================
    @resaas_action(detail=False, methods=["post"])
    def match(self, request, *args, **kwargs):
        candidates = find_candidates(request.data)

        results = []
        for candidate in candidates:
            person = candidate["person"]
            results.append({
                **PersonSerializer(person, context={"request": request}).data,
                "matched_fields": candidate["matched_fields"],
                "documents": DocumentSerializer(
                    person.documents.all(), many=True, context={"request": request}
                ).data,
            })

        return all_response(request, results=results)

    # ======================================================
    # POST /api/django_resaas/persons/<id>/add_document/
    # Attach one new Document to an EXISTING Person - the same
    # person.documents.create(...) call employee_registration_service
    # already uses for a brand new Person during add_employee, exposed
    # here so change_employee (or any future edit flow for a Person
    # that already exists) can add a document too, without a second
    # Document-creation mechanism. Deliberately generic to Person, not
    # Employee, per CLAUDE.md's "would this still make sense without
    # the requesting module" test - a future Patient/Student edit flow
    # can reuse this exact action.
    #
    # This action's own base permission (add_document_person, from the
    # decorator's default action_name-based codename) only gates "may
    # call this endpoint at all" - the real, reused add_document
    # permission (the same one add_employee's register() already
    # requires for a brand new Person's documents) is checked
    # explicitly below, same double-check pattern as register().
    # ======================================================
    @resaas_action(detail=True, methods=["post"])
    def add_document(self, request, *args, **kwargs):
        if not isPermited(request=request, role="add_document"):
            return Response(
                {"detail": f"{Translate.tdc(request, 'Missing permission(s)')}: add_document."},
                status=status.HTTP_403_FORBIDDEN,
            )

        person = self.get_object()

        tipo_id = request.data.get("tipo")
        numero = request.data.get("numero")

        if not tipo_id or not numero:
            return Response(
                {"detail": Translate.tdc(request, "tipo and numero are required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not DocumentType.objects.filter(id=tipo_id).exists():
            return Response(
                {"detail": Translate.tdc(request, "tipo not found.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document = person.documents.create(
                tipo_id=tipo_id,
                numero=numero,
                data_emissao=request.data.get("data_emissao") or None,
                data_validade=request.data.get("data_validade") or None,
                arquivo=request.FILES.get("arquivo"),
                created_by=request.user,
                updated_by=request.user,
            )
        except (ValidationError, IntegrityError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

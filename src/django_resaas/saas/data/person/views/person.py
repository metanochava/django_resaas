
# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from django_resaas.saas.models.person import Person
from django_resaas.saas.models.document import Document
from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.core.decorators.action import resaas_action
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

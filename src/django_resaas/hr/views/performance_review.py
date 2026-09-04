# hr/views/performance_review.py

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

from django_resaas.engine.core.base.views import BaseAPIView, registerView
from django_resaas.engine.core.decorators.action import resaas_action

from django_resaas.hr.models.performance_review import PerformanceReview
from django_resaas.hr.serializers.performance_review import PerformanceReviewSerializer
from django_resaas.hr.services import performance_service


@registerView('performancereviews', module='hr')
class PerformanceReviewAPIView(BaseAPIView):
    queryset = PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer

    # get_object() already scopes to the caller's tenant.

    @resaas_action(detail=True, methods=["post"])
    def submit_review(self, request, *args, **kwargs):
        review = self.get_object()

        try:
            with transaction.atomic():
                performance_service.submit_review(review, actor=request.user)
        except performance_service.PerformanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            PerformanceReviewSerializer(review, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

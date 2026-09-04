# hr/views/application.py

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework import status

from django_resaas.engine.core.base.views import BaseAPIView, registerView
from django_resaas.engine.core.decorators.action import resaas_action

from django_resaas.hr.models.application import Application
from django_resaas.hr.models.employee import Employee
from django_resaas.hr.serializers.application import ApplicationSerializer
from django_resaas.hr.serializers.employee import EmployeeSerializer
from django_resaas.hr.services import recruitment_service


@registerView('applications', module='hr')
class ApplicationAPIView(BaseAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

    # get_object() already scopes to the caller's tenant (get_queryset()
    # filters by entity_id/branch_id - see BaseAPIView), so an Entity can
    # never move/schedule-interview/hire an Application it can't already
    # see (same guarantee check_in/check_out and the LeaveRequest actions
    # rely on).

    @resaas_action(detail=True, methods=["post"])
    def move(self, request, *args, **kwargs):
        application = self.get_object()
        target_status = request.data.get("status")

        if not target_status:
            return Response(
                {"status": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                recruitment_service.move(
                    application, target_status=target_status, actor=request.user
                )
        except recruitment_service.RecruitmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ApplicationSerializer(application, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @resaas_action(detail=True, methods=["post"])
    def schedule_interview(self, request, *args, **kwargs):
        application = self.get_object()

        scheduled_at = parse_datetime(request.data.get("scheduled_at") or "")
        if scheduled_at is None:
            return Response(
                {"scheduled_at": "A valid ISO datetime is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at)

        interviewer = None
        interviewer_id = request.data.get("interviewer")
        if interviewer_id:
            interviewer = Employee.objects.filter(
                id=interviewer_id, entity_id=request.entity_id
            ).first()
            if interviewer is None:
                return Response(
                    {"interviewer": "Does not belong to the current entity."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                interview = recruitment_service.schedule_interview(
                    application,
                    scheduled_at=scheduled_at,
                    actor=request.user,
                    interviewer=interviewer,
                    mode=request.data.get("mode"),
                    notes=request.data.get("notes") or "",
                )
        except recruitment_service.RecruitmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        from django_resaas.hr.serializers.interview import InterviewSerializer

        return Response(
            InterviewSerializer(interview, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @resaas_action(detail=True, methods=["post"])
    def hire(self, request, *args, **kwargs):
        application = self.get_object()

        try:
            with transaction.atomic():
                employee = recruitment_service.hire(application, actor=request.user)
        except recruitment_service.RecruitmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            EmployeeSerializer(employee, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

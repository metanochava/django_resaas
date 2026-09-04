# hr/views/employee.py

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

from django_resaas.engine.core.base.views import BaseAPIView, registerView
from django_resaas.engine.core.decorators.action import resaas_action
from django_resaas.engine.models.entity import Entity

from django_resaas.hr.models.employee import Employee
from django_resaas.hr.models.attendance import AttendanceSource
from django_resaas.hr.models.onboarding_template import OnboardingTemplate
from django_resaas.hr.serializers.employee import EmployeeSerializer
from django_resaas.hr.serializers.attendance import AttendanceSerializer
from django_resaas.hr.serializers.employee_onboarding import EmployeeOnboardingSerializer
from django_resaas.hr.services.employee_number_service import EmployeeNumberService
from django_resaas.hr.services import attendance_service
from django_resaas.hr.services import onboarding_service


@registerView('employees', module='hr')
class EmployeeAPIView(BaseAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def perform_create(self, serializer):
        data = {
            "created_by": self.request.user,
            "updated_by": self.request.user,
            "entity_id": self.request.entity_id,
            "branch_id": self.request.branch_id,
        }

        with transaction.atomic():
            if not serializer.validated_data.get("code"):
                entity = Entity.objects.get(id=self.request.entity_id)
                data["code"] = EmployeeNumberService.generate(entity)

            serializer.save(**data)

    # =========================
    # ATTENDANCE
    # =========================
    # get_object() already scopes to the caller's tenant (get_queryset()
    # filters by entity_id/branch_id - see BaseAPIView), so an Entity
    # can never check-in/check-out an Employee it can't already see.

    @resaas_action(detail=True, methods=["post"])
    def check_in(self, request, *args, **kwargs):
        employee = self.get_object()
        source = request.data.get("source") or AttendanceSource.MANUAL

        try:
            with transaction.atomic():
                attendance = attendance_service.check_in(
                    employee, source=source, actor=request.user
                )
        except attendance_service.AttendanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            AttendanceSerializer(attendance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @resaas_action(detail=True, methods=["post"])
    def check_out(self, request, *args, **kwargs):
        employee = self.get_object()

        try:
            with transaction.atomic():
                attendance = attendance_service.check_out(
                    employee, actor=request.user
                )
        except attendance_service.AttendanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            AttendanceSerializer(attendance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    # =========================
    # ONBOARDING
    # =========================

    @resaas_action(detail=True, methods=["post"])
    def start_onboarding(self, request, *args, **kwargs):
        employee = self.get_object()

        template = None
        template_id = request.data.get("template")

        if template_id:
            try:
                template = OnboardingTemplate.objects.get(
                    id=template_id, entity_id=employee.entity_id,
                )
            except OnboardingTemplate.DoesNotExist:
                return Response(
                    {"detail": "Onboarding template not found for this entity."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                onboarding = onboarding_service.start_onboarding(
                    employee, template=template, actor=request.user
                )
        except onboarding_service.OnboardingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            EmployeeOnboardingSerializer(onboarding, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

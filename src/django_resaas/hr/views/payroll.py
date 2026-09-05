# hr/views/payroll.py

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

from django_resaas.engine.core.base.views import BaseAPIView, registerView
from django_resaas.engine.core.decorators.action import resaas_action

from django_resaas.hr.models.payroll import Payroll
from django_resaas.hr.serializers.payroll import PayrollSerializer
from django_resaas.hr.serializers.payslip import PayslipSerializer
from django_resaas.hr.services import payroll_service


@registerView('payrolls', module='hr')
class PayrollAPIView(BaseAPIView):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer

    def _run(self, request, func):
        payroll = self.get_object()

        try:
            with transaction.atomic():
                func(payroll, actor=request.user)
        except payroll_service.PayrollError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            PayrollSerializer(payroll, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @resaas_action(detail=True, methods=["post"])
    def calculate(self, request, *args, **kwargs):
        return self._run(request, payroll_service.calculate_payroll)

    @resaas_action(detail=True, methods=["post"])
    def review(self, request, *args, **kwargs):
        return self._run(request, payroll_service.review_payroll)

    @resaas_action(detail=True, methods=["post"])
    def reopen(self, request, *args, **kwargs):
        return self._run(request, payroll_service.reopen_payroll)

    @resaas_action(detail=True, methods=["post"])
    def confirm(self, request, *args, **kwargs):
        payroll = self.get_object()

        try:
            # confirm_payroll manages its own transaction/row lock - see
            # hr/services/payroll_service.py.
            payroll, payslip = payroll_service.confirm_payroll(payroll, actor=request.user)
        except payroll_service.PayrollError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        data = PayrollSerializer(payroll, context={"request": request}).data
        data["payslip"] = PayslipSerializer(payslip, context={"request": request}).data

        return Response(data, status=status.HTTP_200_OK)

    @resaas_action(detail=True, methods=["post"])
    def mark_paid(self, request, *args, **kwargs):
        return self._run(request, payroll_service.mark_paid)

    @resaas_action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        return self._run(request, payroll_service.cancel_payroll)

    # =========================
    # REPORTS (Fase 10)
    # =========================
    # Reusa a acao generica pdflist() de BaseAPIView - so enriquece o
    # contexto (total liquido) para o template hr/payroll_list.html.

    def get_pdflist_context(self, request, queryset):
        context = super().get_pdflist_context(request, queryset)

        context["section_title"] = "Payroll Register"
        context["total_net_salary"] = sum(
            (payroll.net_salary or 0) for payroll in queryset
        )

        return context

"""One place where every RESAAS view gets the same response behaviour:
the RESAAS exception handler (the `error` contract) and the request's alerts
merged into the body. Mixed into BaseAPIView and ExplicitAccessMixin; other
APIViews can add it when they need `add_alert`."""
from django_resaas.saas.core.alerts import merge_alerts
from django_resaas.saas.core.exceptions.handler import resaas_exception_handler


class ResaasResponseMixin:

    def get_exception_handler(self):
        return resaas_exception_handler

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        data = getattr(response, "data", None)

        if isinstance(data, dict) and not getattr(response, "is_rendered", False):
            merged = merge_alerts(request, data)

            if merged is not data:
                response.data = merged

        return response

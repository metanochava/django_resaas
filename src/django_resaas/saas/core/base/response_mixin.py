"""One place where every RESAAS view gets the same response behaviour:
the RESAAS exception handler (the `error` contract), the request's alerts
merged into the body, and the status of a successful POST. Mixed into
BaseAPIView and ExplicitAccessMixin; every other APIView that accepts POST
adds it too (tests/test_rest_architecture.py guards that).

Status of a successful POST (a POST never answers 200; PATCH/PUT keep 200
with the record, DELETE keeps 204):
    201  a record was created (the view says so: CreateModelMixin, Response(status=201))
    202  an operation ran and the body carries its result (check-in, approve, login, ...)
    204  an operation ran and there is nothing to return
A view that answers a POST with a plain 200 is moved to 202 / 204 here, so
no view has to remember it."""
from rest_framework import status
from rest_framework.response import Response

from django_resaas.saas.core.alerts import merge_alerts
from django_resaas.saas.core.exceptions.handler import resaas_exception_handler


def _is_empty(data):
    return data is None or data == "" or data == {} or data == []


class ResaasResponseMixin:

    def get_exception_handler(self):
        return resaas_exception_handler

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        data = getattr(response, "data", None)

        if isinstance(data, dict) and not getattr(response, "is_rendered", False):
            merged = merge_alerts(request, data)

            if merged is not data:
                response.data = data = merged

        if (
            request.method == "POST"
            and response.status_code == status.HTTP_200_OK
            and isinstance(response, Response)
            and not getattr(response, "is_rendered", False)
        ):
            if _is_empty(data):
                response.status_code = status.HTTP_204_NO_CONTENT
                response.data = None
            else:
                response.status_code = status.HTTP_202_ACCEPTED

        return response

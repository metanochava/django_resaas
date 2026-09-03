from django_resaas.engine.core.utils import build_select_data, all
from rest_framework.response import Response

class SelectMixin:

    def is_select_mode(self):
        return self.request.query_params.get("select") == "true"

    def get_select_response(self, queryset):
        page = self.paginate_queryset(queryset)

        if page is not None:
            data = build_select_data(page)
            return self.get_paginated_response(data)

        data = build_select_data(queryset)
        return Response(data)
from django_resaas.saas.core.utils import build_select_data
from rest_framework.response import Response

class SelectMixin:

    def is_select_mode(self):
        return self.request.query_params.get("select") == "true"

    def is_preview_mode(self):
        return self.request.query_params.get("preview") == "true"

    def get_select_response(self, queryset):
        preview = None

        # ?select=true&preview=true - the related model's own RESAAS.preview
        # (relation pickers). No declared preview -> plain label/value rows.
        if self.is_preview_mode():
            from django_resaas.saas.core.utils.relation_preview import (
                get_relation_preview_config,
                preview_select_related,
            )

            preview = get_relation_preview_config(queryset.model)

            if preview:
                related = preview_select_related(queryset.model, preview)
                if related:
                    queryset = queryset.select_related(*related)

        page = self.paginate_queryset(queryset)

        if page is not None:
            data = build_select_data(page, self.request, preview)
            return self.get_paginated_response(data)

        data = build_select_data(queryset, self.request, preview)
        return Response(data)

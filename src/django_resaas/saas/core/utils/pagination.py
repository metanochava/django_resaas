from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ResaasPagination(PageNumberPagination):

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000

    no_pagination = False

    def paginate_queryset(
        self,
        queryset,
        request,
        view=None
    ):

        page_size = request.query_params.get(
            self.page_size_query_param
        )

        # page_size=0 -> devolver todos
        if page_size == "0":

            self.no_pagination = True
            self.count = queryset.count()

            return list(queryset)

        self.no_pagination = False

        return super().paginate_queryset(
            queryset,
            request,
            view
        )

    def get_paginated_response(self, data):

        if self.no_pagination:

            return Response({
                "count": self.count,
                "next": None,
                "previous": None,
                "results": data,
            })

        return super().get_paginated_response(
            data
        )
from django_resaas.saas.core.dashboards.providers import (
    BaseDashboardProvider,
    register_provider,
)

from dev.demo.models import Product


@register_provider("demo.total_products")
class TotalProductsProvider(BaseDashboardProvider):
    """Widget 'stat' de exemplo - também usado pelos testes do motor de
    dashboards (test_dashboard_saas.py) como app real e mínima com
    dashboard.py, sem depender de nenhum módulo de negócio."""

    def resolve(self):
        qs = self.scoped_queryset(Product.objects.all())

        search = self.filters.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        value = qs.count()

        return {
            "value": value,
            "formatted_value": str(value),
        }


@register_provider("demo.products_table")
class ProductsTableProvider(BaseDashboardProvider):
    """Widget 'table' de exemplo - paginação no servidor (nunca carrega
    a tabela inteira), mesmo contrato de paginação de ResaasPagination
    (count/next/previous), que o frontend já sabe mapear para
    rowsNumber (ver AutoTable.vue)."""

    def resolve(self):
        qs = self.scoped_queryset(Product.objects.all()).order_by("-created_at")

        search = self.filters.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        page = int(self.request.query_params.get("page") or 1)
        page_size = int(self.request.query_params.get("page_size") or 10)

        total = qs.count()
        start = (page - 1) * page_size

        rows = list(
            qs[start:start + page_size].values("id", "name", "sku", "price")
        )

        return {
            "columns": [
                {"name": "name", "label": "Nome"},
                {"name": "sku", "label": "SKU"},
                {"name": "price", "label": "Preço"},
            ],
            "rows": rows,
            "pagination": {
                "count": total,
                "next": start + page_size < total,
                "previous": page > 1,
            },
        }

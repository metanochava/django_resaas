"""
Regression: Branch.RESAAS.routes had a typo ("change_banch",
"view_banch", "add_banch", and even "list" pointing at "add_banch")
that didn't match any real Vue route name (branchRoute.js registers
list_branch/add_branch/change_branch/view_branch). AutoTable.vue's
generic row-click navigation reads exactly this schema value
(config.routes.view) - with the typo, it always fell through to its
"route_inexistente" fallback instead of ever reaching BranchSEPage.vue.
"""
import pytest

from django_resaas.saas.core.schema.builder import ResaasSchemaBuilder
from django_resaas.saas.models.branch import Branch

pytestmark = pytest.mark.django_db


def test_branch_routes_match_the_real_vue_route_names():
    routes = ResaasSchemaBuilder(Model=Branch, fields=[]).build_routes()

    assert routes == {
        "list": "list_branch",
        "add": "add_branch",
        "change": "change_branch",
        "view": "view_branch",
    }

"""The phone's bottom tabs (core/services/mobile_tab_service.py): per Entity
Type with an Entity override, filtered by the CURRENT profile like the menus,
at most MAX_TABS; seeded from the modules' <app>/mobile_tabs.py; listed per
Entity Type (?entity_type=) for its page."""
from types import SimpleNamespace
from unittest import mock

import pytest

from django_resaas.saas.core.services import mobile_tab_service
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.mobile_tab import EntityMobileTab, EntityTypeMobileTab

pytestmark = pytest.mark.django_db

# a module and permissions every bootstrapped tenant has (Root holds them all)
APP = "django_resaas"


def _request(tenant):
    return SimpleNamespace(
        user=tenant["user"], entity_type_id=tenant["entity"].entity_type_id, entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id, group_id=tenant["root_group"].id,
    )


def _type_tab(tenant, route, order=10, **kwargs):
    defaults = {"label": route.title(), "icon": "star", "permission": "list_branch", "app": APP, "active": True}
    defaults.update(kwargs)
    return EntityTypeMobileTab.objects.create(
        entity_type_id=tenant["entity"].entity_type_id, route=route, order=order, **defaults,
    )


def _routes(tenant):
    return [tab["route"] for tab in mobile_tab_service.tabs_for(_request(tenant))]


class TestTabsFor:

    def test_the_entity_types_tabs_in_order(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-order")
        _type_tab(tenant, "list_user", order=20)
        _type_tab(tenant, "list_branch", order=10)

        assert _routes(tenant) == ["list_branch", "list_user"]

    def test_a_tab_needs_its_permission_in_the_current_profile(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-perm")
        _type_tab(tenant, "list_branch")
        _type_tab(tenant, "secret", permission="no_such_permission")

        assert _routes(tenant) == ["list_branch"]

    def test_inactive_tabs_and_unknown_apps_are_left_out(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-inactive")
        _type_tab(tenant, "list_branch")
        _type_tab(tenant, "off", active=False)
        _type_tab(tenant, "ghost", app="no_such_app")

        assert _routes(tenant) == ["list_branch"]

    def test_at_most_five(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-max")
        for i in range(7):
            _type_tab(tenant, f"route_{i}", order=i)

        assert mobile_tab_service.MAX_TABS == 5
        assert _routes(tenant) == [f"route_{i}" for i in range(5)]

    def test_the_entitys_own_tabs_replace_its_types(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-own")
        _type_tab(tenant, "list_branch")
        EntityMobileTab.objects.create(
            entity=tenant["entity"], route="list_user", label="Users", icon="people",
            permission="list_user", app=APP,
        )

        assert _routes(tenant) == ["list_user"]

    def test_an_inactive_profile_has_no_tabs(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-profile-off")
        _type_tab(tenant, "list_branch")
        BranchUserGroup.objects.filter(user=tenant["user"], group=tenant["root_group"]).update(state="Inactive")

        assert _routes(tenant) == []

    def test_the_endpoint_answers_the_current_profiles_tabs(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-endpoint")
        _type_tab(tenant, "list_branch")

        response = tenant["client"].get(f"/api/django_resaas/users/{tenant['user'].id}/mobile_tabs/")

        assert response.status_code == 200
        assert [tab["route"] for tab in response.data] == ["list_branch"]


class TestSeed:

    CANDIDATES = [
        {"label": "Branches", "icon": "store", "route": "list_branch", "permission": "list_branch", "order": 10, "app": APP},
        {"label": "Users", "icon": "people", "route": "list_user", "permission": "list_user", "order": 20, "app": APP},
    ]

    def _seed(self, entity_type, replace=False):
        def candidates(config):
            return self.CANDIDATES if config.label == APP else []

        with mock.patch.object(mobile_tab_service, "candidates", side_effect=candidates):
            return mobile_tab_service.seed_entity_type(entity_type, replace=replace)

    def test_copies_the_active_modules_candidates_once(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-seed")
        entity_type = EntityType.objects.get(id=tenant["entity"].entity_type_id)

        assert self._seed(entity_type) == 2
        assert self._seed(entity_type) == 0
        assert list(EntityTypeMobileTab.objects.filter(entity_type=entity_type).values_list("route", flat=True)) \
            == ["list_branch", "list_user"]

    def test_replace_starts_again_from_the_candidates(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-seed-replace")
        entity_type = EntityType.objects.get(id=tenant["entity"].entity_type_id)
        _type_tab(tenant, "handmade")

        assert self._seed(entity_type) == 0
        assert self._seed(entity_type, replace=True) == 2
        assert not EntityTypeMobileTab.objects.filter(entity_type=entity_type, route="handmade").exists()


class TestListPerEntityType:

    def test_lists_only_the_requested_entity_types_tabs(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-list")
        other = EntityType.objects.create(name="Other Type", state="Active")
        _type_tab(tenant, "list_user", order=20)
        _type_tab(tenant, "list_branch", order=10)
        EntityTypeMobileTab.objects.create(entity_type=other, route="elsewhere", label="X", permission="list_branch", app=APP)

        response = tenant["client"].get(
            "/api/django_resaas/entitytypemobiletabs/",
            {"entity_type": str(tenant["entity"].entity_type_id), "page_size": 100},
        )

        assert response.status_code == 200
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        assert [row["route"] for row in rows] == ["list_branch", "list_user"]

    def test_a_malformed_entity_type_is_a_400(self, bootstrap_tenant):
        tenant = bootstrap_tenant("mt-list-bad")
        _type_tab(tenant, "list_branch")

        response = tenant["client"].get("/api/django_resaas/entitytypemobiletabs/", {"entity_type": "not-a-uuid"})

        assert response.status_code == 400 and "entity_type" in response.data["error"]["details"]

"""QR card PDF of an Entity / Branch (core/services/qr_card_service.py):
what the QR code opens, the brand colour guard, and the two endpoints
(GET entitys/{id}/pdf/ - pdf_entity, GET branchs/{id}/pdf/ - pdf_branch),
scoped to the current Entity."""
from types import SimpleNamespace

import pytest

from django_resaas.saas.core.services import qr_card_service
from django_resaas.saas.models.branch import Branch

API = "/api/django_resaas"


class TestTargets:
    def test_only_http_websites_are_followed(self):
        assert qr_card_service.safe_site_url("https://clinic.example") == "https://clinic.example"
        assert qr_card_service.safe_site_url("javascript:alert(1)") is None
        assert qr_card_service.safe_site_url("/relative") is None
        assert qr_card_service.safe_site_url(None) is None

    def test_coordinates_give_directions(self):
        address = SimpleNamespace(latitude=-25.96, longitude=32.58, place_id="", formatted_address="")
        url = qr_card_service.address_map_url(address)
        assert url.startswith("https://www.google.com/maps/dir/?")
        assert "destination=-25.96%2C32.58" in url

    def test_place_id_then_formatted_address(self):
        by_place = SimpleNamespace(latitude=None, longitude=None, place_id="abc", formatted_address="Av. 1")
        by_text = SimpleNamespace(latitude=None, longitude=None, place_id="", formatted_address="Av. 1")
        assert "query_place_id=abc" in qr_card_service.address_map_url(by_place, "Shop")
        assert "query=Av.+1" in qr_card_service.address_map_url(by_text)
        assert qr_card_service.address_map_url(None) is None

    def test_the_colour_must_be_hex(self):
        def entity(primary):
            return SimpleNamespace(theme=SimpleNamespace(primary=primary), entity_type=None)

        assert qr_card_service.brand_color(entity("#0f766e")) == "#0f766e"
        assert qr_card_service.brand_color(entity("red;}@import url(http://x)")) == qr_card_service.DEFAULT_COLOR
        assert qr_card_service.brand_color(SimpleNamespace(theme=None, entity_type=None)) == qr_card_service.DEFAULT_COLOR


@pytest.mark.django_db
class TestEndpoints:
    def test_entity_site_first_then_branch_location(self, bootstrap_tenant):
        tenant = bootstrap_tenant("qr-card-entity")
        entity, branch = tenant["entity"], tenant["branch"]

        assert qr_card_service.entity_target(entity) == (None, None)

        branch.set_address(latitude="-25.960000", longitude="32.580000")
        kind, url = qr_card_service.entity_target(entity)
        assert kind == "map" and "destination=" in url

        entity.site = "https://clinic.example"
        entity.save()
        assert qr_card_service.entity_target(entity) == ("site", "https://clinic.example")
        # the Branch prefers its own location, the website is its fallback
        assert qr_card_service.branch_target(branch)[0] == "map"

    def test_entity_pdf_is_the_qr_card(self, bootstrap_tenant):
        tenant = bootstrap_tenant("qr-card-pdf")
        tenant["entity"].site = "https://clinic.example"
        tenant["entity"].save()

        response = tenant["client"].get(f"{API}/entitys/{tenant['entity'].id}/pdf/")

        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"

    def test_branch_pdf(self, bootstrap_tenant):
        tenant = bootstrap_tenant("qr-card-branch")
        tenant["branch"].set_address(latitude="-25.960000", longitude="32.580000")

        response = tenant["client"].get(f"{API}/branchs/{tenant['branch'].id}/pdf/")

        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"

    def test_another_entitys_branch_is_not_found(self, bootstrap_tenant):
        a = bootstrap_tenant("qr-card-a")
        b = bootstrap_tenant("qr-card-b")

        assert a["client"].get(f"{API}/branchs/{b['branch'].id}/pdf/").status_code == 404

    def test_card_without_target_explains_what_is_missing(self, bootstrap_tenant):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        tenant = bootstrap_tenant("qr-card-missing")
        context = qr_card_service.card_context(RequestFactory().get("/"), tenant["entity"])
        html = render_to_string("django_resaas/pdf/qr_card.html", context)

        assert context["qr_b64"] is None
        assert 'class="missing"' in html
        assert Branch.objects.filter(entity=tenant["entity"]).exists()

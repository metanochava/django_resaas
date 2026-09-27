"""Contact form of an Entity's public site.

- POST site/contact/ is PUBLIC: the Entity comes from the request Origin
  (like GET site/), never from the body; throttled per client address.
- The message is stored and `site.contact_message.received` is emitted
  (notifications rules decide who is told).
- Staff read them through sitecontactmessages/ (BaseAPIView, entity scope).
"""
import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from django_resaas.saas.core.events import EventDispatcher
from django_resaas.saas.core.services.site_service import CONTACT_MESSAGE_RECEIVED
from django_resaas.saas.models.site_contact_message import SiteContactMessage
from django_resaas.saas.tests.test_relations_endpoint import _client_with

pytestmark = pytest.mark.django_db

URL = "/api/site/contact/"
BODY = {"name": "Ana", "phone": "+258 84 000 0000", "message": "I would like an appointment."}


@pytest.fixture(autouse=True)
def _fresh_throttle():
    cache.clear()
    yield
    cache.clear()


def _site(tenant, host):
    entity = tenant["entity"]
    entity.site = f"http://{host}"      # stored with http even when served over https
    entity.save(update_fields=["site"])
    return entity


def _post(body=None, origin="https://clinic-a.test", **extra):
    return APIClient().post(URL, body if body is not None else BODY, format="json", HTTP_ORIGIN=origin, **extra)


class TestPublicContactForm:

    def test_the_message_goes_to_the_entity_of_the_site(self, bootstrap_tenant):
        entity = _site(bootstrap_tenant("contact-a"), "clinic-a.test")

        response = _post()

        assert response.status_code == 201, response.data
        message = SiteContactMessage.objects.get()
        assert message.entity_id == entity.id
        assert message.site == "clinic-a.test"
        assert message.status == SiteContactMessage.STATUS_NEW
        assert (message.name, message.phone, message.email) == ("Ana", "+258 84 000 0000", None)

    def test_the_body_cannot_choose_the_entity(self, bootstrap_tenant):
        mine = _site(bootstrap_tenant("contact-mine"), "clinic-a.test")
        other = bootstrap_tenant("contact-other")["entity"]

        _post({**BODY, "entity": str(other.id), "entity_id": str(other.id)})

        assert SiteContactMessage.objects.get().entity_id == mine.id

    def test_an_unknown_site_is_404(self, bootstrap_tenant):
        _site(bootstrap_tenant("contact-known"), "clinic-a.test")

        response = _post(origin="https://unknown.test")

        assert response.status_code == 404
        assert response.data["error"]["code"] == "site_not_found"
        assert not SiteContactMessage.objects.exists()

    def test_a_phone_or_an_email_is_required(self, bootstrap_tenant):
        _site(bootstrap_tenant("contact-reach"), "clinic-a.test")

        response = _post({"name": "Ana", "message": "Hello"})

        assert response.status_code == 400
        assert set(response.data["error"]["details"]) >= {"phone", "email"}

    def test_a_filled_honeypot_is_answered_but_not_stored(self, bootstrap_tenant):
        _site(bootstrap_tenant("contact-bot"), "clinic-a.test")

        response = _post({**BODY, "website": "http://spam.example"})

        assert response.status_code == 201
        assert not SiteContactMessage.objects.exists()

    @override_settings(RESAAS_SITE_CONTACT_THROTTLE_RATE="2/hour")
    def test_it_is_throttled_per_address(self, bootstrap_tenant):
        _site(bootstrap_tenant("contact-throttle"), "clinic-a.test")

        codes = [_post().status_code for _ in range(3)]

        assert codes == [201, 201, 429]
        assert SiteContactMessage.objects.count() == 2

    def test_the_event_is_emitted_with_the_message(self, bootstrap_tenant, monkeypatch):
        entity = _site(bootstrap_tenant("contact-event"), "clinic-a.test")
        seen = []
        monkeypatch.setattr(
            EventDispatcher, "_listeners",
            EventDispatcher._listeners + [(CONTACT_MESSAGE_RECEIVED, seen.append, False)],
        )

        _post()

        assert len(seen) == 1
        assert seen[0]["entity_id"] in (entity.id, str(entity.id))
        assert seen[0]["context"]["message"] == "I would like an appointment."


class TestStaffInbox:

    def _message(self, entity, **extra):
        return SiteContactMessage.objects.create(
            entity=entity, site="clinic.test", name="Ana", phone="1", message="Hi", **extra
        )

    def test_staff_only_see_their_entitys_messages(self, bootstrap_tenant):
        tenant = bootstrap_tenant("inbox-a")
        other = bootstrap_tenant("inbox-b")
        mine = self._message(tenant["entity"])
        self._message(other["entity"])

        response = _client_with(tenant, ["list_sitecontactmessage"]).get(
            "/api/django_resaas/sitecontactmessages/?format=json"
        )

        assert response.status_code == 200, response.data
        rows = response.data.get("results", response.data)
        assert [str(r["id"]) for r in rows] == [str(mine.id)]

    def test_without_permission_it_is_403(self, bootstrap_tenant):
        tenant = bootstrap_tenant("inbox-denied")

        response = _client_with(tenant, []).get("/api/django_resaas/sitecontactmessages/?format=json")

        assert response.status_code == 403

    def test_marking_it_handled_records_who_and_when(self, bootstrap_tenant):
        tenant = bootstrap_tenant("inbox-handle")
        message = self._message(tenant["entity"])
        client = _client_with(tenant, ["change_sitecontactmessage", "view_sitecontactmessage"])

        response = client.patch(
            f"/api/django_resaas/sitecontactmessages/{message.id}/",
            {"status": "handled", "message": "rewritten"}, format="json",
        )

        assert response.status_code == 200, response.data
        message.refresh_from_db()
        assert message.status == "handled"
        assert message.handled_by_id == tenant["user"].id
        assert message.handled_at is not None
        assert message.message == "Hi"           # what the visitor wrote is read only

    def test_staff_cannot_create_messages(self, bootstrap_tenant):
        tenant = bootstrap_tenant("inbox-create")
        client = _client_with(tenant, ["add_sitecontactmessage"])

        response = client.post("/api/django_resaas/sitecontactmessages/", {**BODY}, format="json")

        assert response.status_code == 405
        assert not SiteContactMessage.objects.exists()


class TestSiteBranches:
    """GET site/branches/ (PUBLIC): the site's Entity branches for its map."""

    def test_the_branches_of_the_site_with_their_location(self, bootstrap_tenant):
        tenant = bootstrap_tenant("branches-a")
        _site(tenant, "clinic-a.test")
        tenant["branch"].set_address(latitude="-25.9639738", longitude="32.5866938",
                                     formatted_address="Av. Example 1, Maputo")
        other = bootstrap_tenant("branches-b")
        other["branch"].set_address(latitude="1", longitude="2")

        response = APIClient().get("/api/site/branches/", HTTP_ORIGIN="https://clinic-a.test")

        assert response.status_code == 200, response.data
        assert response.data == [{
            "id": str(tenant["branch"].id),
            "name": tenant["branch"].name,
            "description": tenant["branch"].description or None,
            "address": "Av. Example 1, Maputo",
            "coordinates": {"lat": -25.963974, "lng": 32.586694},   # Address keeps 6 decimals
        }]

    def test_a_branch_without_address_has_no_coordinates(self, bootstrap_tenant):
        tenant = bootstrap_tenant("branches-none")
        _site(tenant, "clinic-a.test")

        rows = APIClient().get("/api/site/branches/", HTTP_ORIGIN="https://clinic-a.test").data

        assert [(r["address"], r["coordinates"]) for r in rows] == [(None, None)]

    def test_an_unknown_site_is_404(self, bootstrap_tenant):
        _site(bootstrap_tenant("branches-unknown"), "clinic-a.test")

        response = APIClient().get("/api/site/branches/", HTTP_ORIGIN="https://unknown.test")

        assert response.status_code == 404
        assert response.data["error"]["code"] == "site_not_found"

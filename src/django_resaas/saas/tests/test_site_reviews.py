"""Google reviews of a public site (GET site/reviews/): PUBLIC, the Entity
comes from the request Origin, the server calls the Places API with its own
key, normalizes and caches the answer; no place or no key -> no reviews."""
import json
import urllib.error
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = "/api/site/reviews/"

PLACE = {
    "displayName": {"text": "Clínica Amal"},
    "rating": 4.7,
    "userRatingCount": 128,
    "googleMapsUri": "https://maps.google.com/?cid=1",
    "reviews": [{
        "rating": 5,
        "text": {"text": "Excellent care."},
        "relativePublishTimeDescription": "2 weeks ago",
        "publishTime": "2026-09-28T10:00:00Z",
        "authorAttribution": {"displayName": "Ana", "uri": "https://maps.google.com/u/1", "photoUri": "https://lh3/x.png"},
    }],
}


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()
    yield
    cache.clear()


def _site(tenant, host="clinic-a.test", place="ChIJ-place"):
    entity = tenant["entity"]
    entity.site = f"http://{host}"
    entity.google_place_id = place
    entity.save(update_fields=["site", "google_place_id"])
    return entity


def _get(origin="https://clinic-a.test", **params):
    return APIClient().get(URL, params, HTTP_ORIGIN=origin)


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@override_settings(RESAAS_GOOGLE_PLACES_API_KEY="server-key")
def test_reviews_of_the_site_place_are_normalized_and_cached(bootstrap_tenant):
    _site(bootstrap_tenant("reviews-a"))
    with mock.patch("urllib.request.urlopen", return_value=_Response(PLACE)) as urlopen:
        first = _get(lang="pt-pt")
        second = _get(lang="pt-pt")

    assert first.status_code == 200
    data = first.json()
    assert data["enabled"] is True and data["rating"] == 4.7 and data["total"] == 128
    assert data["reviews"][0] == {
        "author": "Ana", "author_url": "https://maps.google.com/u/1", "photo": "https://lh3/x.png",
        "rating": 5, "text": "Excellent care.", "relative_time": "2 weeks ago", "time": "2026-09-28T10:00:00Z",
    }
    assert second.json() == data
    assert urlopen.call_count == 1  # cached

    request = urlopen.call_args[0][0]
    assert "ChIJ-place" in request.full_url and "languageCode=pt" in request.full_url
    assert request.get_header("X-goog-api-key") == "server-key"
    assert "server-key" not in json.dumps(data)


def test_without_key_or_place_there_are_no_reviews(bootstrap_tenant):
    _site(bootstrap_tenant("reviews-b"))
    with mock.patch("urllib.request.urlopen") as urlopen:
        assert _get().json() == {"enabled": False, "name": None, "rating": None, "total": 0, "url": None, "reviews": []}
    urlopen.assert_not_called()

    with override_settings(RESAAS_GOOGLE_PLACES_API_KEY="k"):
        tenant = bootstrap_tenant("reviews-c")
        _site(tenant, host="clinic-c.test", place="")
        assert _get(origin="https://clinic-c.test").json()["enabled"] is False


@override_settings(RESAAS_GOOGLE_PLACES_API_KEY="k")
def test_google_failure_answers_no_reviews(bootstrap_tenant):
    _site(bootstrap_tenant("reviews-d"))
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        response = _get()
    assert response.status_code == 200
    assert response.json()["reviews"] == []


def test_unknown_site_is_404(bootstrap_tenant):
    assert _get(origin="https://nobody.test").status_code == 404

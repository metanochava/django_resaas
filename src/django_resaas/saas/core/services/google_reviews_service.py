"""
Google reviews of an Entity's place (Entity.google_place_id), for its public
site. Read from the Google Places API (New) - Place Details with the
`reviews` field - with the server's key, never the browser's, and cached.

Settings (all optional):
    RESAAS_GOOGLE_PLACES_API_KEY          the API key (no key = no reviews)
    RESAAS_GOOGLE_REVIEWS_CACHE_SECONDS   cache of a successful answer (6 h)
    RESAAS_GOOGLE_REVIEWS_TIMEOUT         HTTP timeout in seconds (5)

Google returns at most 5 reviews, chosen by Google ("most relevant"); they are
shown as they come, with the author's attribution - see Google's policies
for Places data.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

PLACES_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = "displayName,rating,userRatingCount,googleMapsUri,reviews"
FAILURE_CACHE_SECONDS = 300

EMPTY = {"enabled": False, "name": None, "rating": None, "total": 0, "url": None, "reviews": []}


def _setting(name, default):
    return getattr(settings, name, default)


def _fetch(place_id, language, api_key):
    url = PLACES_URL.format(place_id=urllib.parse.quote(place_id, safe="")) + "?" + urllib.parse.urlencode(
        {"languageCode": language}
    )
    request = urllib.request.Request(url, headers={
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    })
    with urllib.request.urlopen(request, timeout=_setting("RESAAS_GOOGLE_REVIEWS_TIMEOUT", 5)) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize(data):
    reviews = []
    for review in data.get("reviews") or []:
        author = review.get("authorAttribution") or {}
        text = review.get("text") or review.get("originalText") or {}
        reviews.append({
            "author": author.get("displayName") or "",
            "author_url": author.get("uri"),
            "photo": author.get("photoUri"),
            "rating": review.get("rating"),
            "text": text.get("text") or "",
            "relative_time": review.get("relativePublishTimeDescription"),
            "time": review.get("publishTime"),
        })
    return {
        "enabled": True,
        "name": (data.get("displayName") or {}).get("text"),
        "rating": data.get("rating"),
        "total": data.get("userRatingCount") or 0,
        "url": data.get("googleMapsUri"),
        "reviews": reviews,
    }


def get_reviews(entity, language="pt"):
    """{"enabled", "name", "rating", "total", "url", "reviews": [...]} of the
    Entity's Google place. enabled=False (and no reviews) when the Entity has
    no place or the server has no key. A Google failure is logged and answers
    no reviews, cached briefly so a failing API is not called on every visit."""

    place_id = (getattr(entity, "google_place_id", None) or "").strip()
    api_key = _setting("RESAAS_GOOGLE_PLACES_API_KEY", None)
    if not place_id or not api_key:
        return dict(EMPTY)

    language = (language or "pt").split("-")[0][:5]
    key = f"resaas:google_reviews:{place_id}:{language}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        result = _normalize(_fetch(place_id, language, api_key))
        cache.set(key, result, _setting("RESAAS_GOOGLE_REVIEWS_CACHE_SECONDS", 6 * 3600))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        logger.warning("Google reviews unavailable for place %s: %s", place_id, error)
        result = dict(EMPTY, enabled=True)
        cache.set(key, result, FAILURE_CACHE_SECONDS)
    return result

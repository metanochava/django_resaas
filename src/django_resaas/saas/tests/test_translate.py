"""Translate.tdc: the language the frontend sends (a Language id in the L
header) and the key matching rule shared with the frontend's tdc()."""
import pytest
from django.core.cache import cache
from django.test import RequestFactory

from django_resaas.saas.core.utils.translate import Translate
from django_resaas.saas.models.language import Language

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _pt():
    return Language.objects.get_or_create(code="pt-pt", defaults={"name": "Português"})[0]


def test_the_l_header_with_a_language_id_translates():
    request = RequestFactory().get("/", HTTP_L=str(_pt().id))

    assert Translate.tdc(request, "Save") == Translate.tdc("pt-pt", "Save")
    assert Translate.tdc(request, "Save") != "Save"


def test_the_l_header_with_a_code_still_translates():
    _pt()
    request = RequestFactory().get("/", HTTP_L="pt-pt")

    assert Translate.tdc(request, "Save") != "Save"


def test_keys_match_regardless_of_case_like_the_frontend():
    _pt()
    exact = Translate.tdc("pt-pt", "Save")

    assert Translate.tdc("pt-pt", "save") == exact
    assert Translate.tdc("pt-pt", "  SAVE ") == exact


def test_unknown_text_and_language_fall_back_to_the_text():
    request = RequestFactory().get("/", HTTP_L="00000000-0000-0000-0000-000000000000")

    assert Translate.tdc(request, "Nothing like this key") == "Nothing like this key"
    assert Translate.tdc("pt-pt", None) is None

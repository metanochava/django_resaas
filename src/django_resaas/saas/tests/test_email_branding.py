"""E-mails wear the look of the Entity or EntityType they are about
(core/utils/email_branding.py, applied to every template by
render_email_template(request=/entity=))."""
import pytest
from django.test import RequestFactory

from django_resaas.saas.core.utils.email_branding import email_brand
from django_resaas.saas.core.utils.templates import render_email_template
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.theme import Theme

pytestmark = pytest.mark.django_db


def _request(origin):
    return RequestFactory().post("/", HTTP_ORIGIN=origin)


def _themed(obj, primary, header_text="#FFFFFF"):
    obj.theme = Theme.objects.create(name=f"t-{primary}", primary=primary, header_text=header_text)
    obj.save()
    return obj


def test_the_entity_of_the_site_gives_its_theme(bootstrap_tenant):
    entity = bootstrap_tenant("brand-site")["entity"]
    entity.site = "http://clinica.example.test"
    _themed(entity, "#0E7C86")

    brand = email_brand(_request("https://clinica.example.test"))

    assert brand["entity_name"] == entity.name
    assert brand["brand_color"] == "#0E7C86"
    assert brand["brand_text_color"] == "#FFFFFF"
    assert brand["brand_tint"] == "#e7f2f3"


def test_an_entity_without_theme_uses_its_entity_type_theme(bootstrap_tenant):
    entity = bootstrap_tenant("brand-type")["entity"]
    entity.theme = None
    entity.save()
    _themed(entity.entity_type, "#1E3A8A")

    assert email_brand(entity=entity)["brand_color"] == "#1E3A8A"


def test_the_host_subdomain_gives_the_entity_type():
    entity_type = _themed(EntityType.objects.create(name="Farmacia", label="Pharmacy", state="Active"), "#15803D")

    brand = email_brand(_request("https://www.farmacia.example.test"))

    assert brand["entity_name"] == entity_type.label
    assert brand["brand_color"] == "#15803D"


def test_an_unknown_origin_gives_no_branding():
    assert email_brand(_request("https://nothing.example.test")) == {
        "entity_name": None, "logo": None, "brand_color": None, "brand_text_color": None, "brand_tint": None,
    }


def test_a_colour_that_is_not_a_plain_css_colour_is_ignored():
    _themed(EntityType.objects.create(name="Evil", state="Active"), 'red;"><script>alert(1)</script>')

    assert email_brand(_request("https://evil.example.test"))["brand_color"] is None


@pytest.mark.parametrize("key, context", [
    ("OTP_CODE", {"code": "123456"}),
    ("PASSWORD_RESET", {"link": "https://x.test/#/auth/resetpassword/a/b", "button_label": "Reset"}),
    ("BOOTSTRAP_WELCOME", {"login_url": "https://x.test", "button_label": "Open"}),
])
def test_every_template_uses_the_brand(key, context):
    _themed(EntityType.objects.create(name="Seguradora", label="Insurance", state="Active"), "#1E3A8A")

    html = render_email_template(key, context, request=_request("https://seguradora.example.test"))

    assert "#1E3A8A" in html
    assert "#1976d2" not in html
    assert "Insurance" in html


def test_the_caller_context_wins_over_the_brand():
    _themed(EntityType.objects.create(name="Saude", label="Health", state="Active"), "#0E7C86")

    html = render_email_template(
        "OTP_CODE", {"code": "1", "entity_name": "Clinica Amal"}, request=_request("https://saude.example.test"),
    )

    assert "Clinica Amal" in html and "#0E7C86" in html

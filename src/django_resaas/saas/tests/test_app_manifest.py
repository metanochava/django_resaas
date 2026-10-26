"""Installable app (PWA) of an EntityType's domain (core/services/
app_manifest_service.py): GET entitytypes/manifest/?name=&origin= and
GET entitytypes/{id}/app_icon/ - PUBLIC reads of the type's public data."""
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.theme import Theme

API = "/api/django_resaas/entitytypes"
FRONT = "https://farmacia.example.com"


def png(size=(60, 40), color=(200, 30, 30, 255)):
    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def shop_type(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.CORS_ORIGIN_ALLOW_ALL = False
    settings.CORS_ALLOWED_ORIGINS = [FRONT]
    settings.CORS_ALLOWED_ORIGIN_REGEXES = []
    theme = Theme.objects.create(name="Shop theme", primary="#15803D")
    return EntityType.objects.create(
        name="Farmacia", label="Farmácia", theme=theme,
        icon=SimpleUploadedFile("shop.png", png(), content_type="image/png"),
    )


@pytest.mark.django_db
class TestManifest:
    def test_is_public_and_named_after_the_type(self, shop_type):
        response = APIClient().get(f"{API}/manifest/", {"name": "farmacia", "origin": FRONT})

        assert response.status_code == 200
        assert response["Content-Type"] == "application/manifest+json"
        data = response.json()
        assert data["name"] == "Farmácia"
        assert data["display"] == "standalone"
        assert data["theme_color"] == "#15803D"
        assert data["start_url"] == data["scope"] == data["id"] == f"{FRONT}/"
        assert {i["purpose"] for i in data["icons"]} == {"any", "maskable"}
        assert data["icons"][0]["src"] == f"../{shop_type.id}/app_icon/?size=192&purpose=any"

    def test_an_untrusted_origin_is_never_written(self, shop_type):
        data = APIClient().get(f"{API}/manifest/", {"name": "Farmacia", "origin": "https://evil.example"}).json()

        assert "start_url" not in data and "scope" not in data and "id" not in data

    def test_unknown_or_deleted_type_is_not_found(self, shop_type):
        client = APIClient()
        assert client.get(f"{API}/manifest/", {"name": "nothing"}).status_code == 404
        assert client.get(f"{API}/manifest/").status_code == 404

        shop_type.delete()
        assert client.get(f"{API}/manifest/", {"name": "Farmacia"}).status_code == 404

    def test_a_bad_theme_colour_falls_back(self, shop_type):
        shop_type.theme.primary = "red;}"
        shop_type.theme.save()

        data = APIClient().get(f"{API}/manifest/", {"name": "Farmacia"}).json()

        assert data["theme_color"] == "#1976d2"

    def test_without_icon_no_icons_are_listed(self, shop_type):
        shop_type.icon.delete(save=True)

        data = APIClient().get(f"{API}/manifest/", {"name": "Farmacia"}).json()

        assert data["icons"] == []


@pytest.mark.django_db
class TestAppIcon:
    @pytest.mark.parametrize("size", [180, 192, 512])
    def test_square_png_of_the_requested_size(self, shop_type, size):
        response = APIClient().get(f"{API}/{shop_type.id}/app_icon/", {"size": size, "purpose": "maskable"})

        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        image = Image.open(BytesIO(response.content))
        assert image.size == (size, size)
        # the corner is the white background, the centre is the icon
        assert image.convert("RGB").getpixel((0, 0)) == (255, 255, 255)
        assert image.convert("RGB").getpixel((size // 2, size // 2)) == (200, 30, 30)

    def test_other_sizes_are_refused(self, shop_type):
        client = APIClient()
        assert client.get(f"{API}/{shop_type.id}/app_icon/", {"size": 4000}).status_code == 400
        assert client.get(f"{API}/{shop_type.id}/app_icon/", {"purpose": "x"}).status_code == 400

    def test_no_icon_is_not_found(self, shop_type):
        shop_type.icon.delete(save=True)

        assert APIClient().get(f"{API}/{shop_type.id}/app_icon/").status_code == 404

    def test_writes_stay_protected(self, shop_type):
        assert APIClient().post(f"{API}/manifest/", {"name": "Farmacia"}).status_code in (401, 403, 405)

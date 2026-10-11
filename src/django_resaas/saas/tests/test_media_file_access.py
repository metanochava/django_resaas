"""MEDIA_URL access: a token opens only the file it was issued for, and
FileAccessMiddleware answers 401 in the error contract otherwise."""
import json
import time

import pytest
from django.test import RequestFactory, override_settings

from django_resaas.saas.core.middleware.file_access import FileAccessMiddleware
from django_resaas.saas.core.utils.full_path import FullPath

KEY = "test-file-key"


def _settings(**file_token):
    config = {"KEY": KEY, "ENABLE_TEMPORARY": True, "TEMP_TTL": 300, "ENABLE_PERMANENT": True}
    config.update(file_token)
    return override_settings(DJANGO_REST_AUTH={"FILE_TOKEN": config}, MEDIA_URL="/media/")


def _passed(request):
    from django.http import HttpResponse
    return HttpResponse("served", content_type="text/plain")


def _call(url):
    return FileAccessMiddleware(_passed)(RequestFactory().get(url))


def _token(url):
    return url.split("token=")[1]


@pytest.mark.parametrize("temporary", [True, False])
def test_token_opens_only_its_own_file(temporary):
    with _settings():
        request = RequestFactory().get("/api/x/")
        url = FullPath.url(request, "/media/entity/a.png", temporary=temporary)

        assert _call(url).status_code == 200
        assert _call("/media/entity/b.png?token=" + _token(url)).status_code == 401


def test_missing_or_forged_token_is_401_in_error_contract():
    with _settings():
        for url in ("/media/entity/a.png", "/media/entity/a.png?token=0.abc", "/media/entity/a.png?token=x"):
            response = _call(url)
            assert response.status_code == 401
            body = json.loads(response.content)
            assert set(body) == {"error"}
            assert body["error"]["code"] == "file_token_invalid"


def test_expired_token_is_rejected():
    with _settings(TEMP_TTL=-10):
        url = FullPath.url(RequestFactory().get("/"), "/media/a.png", temporary=True)
        assert _call(url).status_code == 401


def test_token_from_another_key_is_rejected():
    with _settings(KEY="other-key"):
        url = FullPath.url(RequestFactory().get("/"), "/media/a.png", temporary=False)
    with _settings():
        assert _call(url).status_code == 401


def test_no_key_means_no_file_urls():
    with override_settings(DJANGO_REST_AUTH={"FILE_TOKEN": {"ENABLE_PERMANENT": True}}):
        assert FullPath.url(RequestFactory().get("/"), "/media/a.png", temporary=False) is None


def test_quoted_file_names_match():
    with _settings():
        url = FullPath.url(RequestFactory().get("/"), "/media/docs/my%20file.pdf", temporary=True)
        assert _call(url).status_code == 200


def test_x_accel_redirect_hands_the_file_to_nginx():
    with _settings(X_ACCEL_REDIRECT="/protected-media/"):
        url = FullPath.url(RequestFactory().get("/"), "/media/docs/my%20file.pdf", temporary=True)
        response = _call(url)

        assert response.status_code == 200
        assert response["X-Accel-Redirect"] == "/protected-media/docs/my%20file.pdf"
        assert "Content-Type" not in response
        assert response.content == b""


def test_path_traversal_is_rejected():
    with _settings(X_ACCEL_REDIRECT="/protected-media/"):
        path = "/media/../settings.py"
        token = FullPath._generate_token(path, int(time.time()) + 60)
        assert _call(path + "?token=" + token).status_code == 401


def test_other_paths_are_not_touched():
    with _settings():
        assert _call("/api/anything/").status_code == 200

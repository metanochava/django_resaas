"""
Direct unit tests for FrontEndMiddleware (the FEK/FEP gate), independent
of any real view - covers the URL-scope policy (including the
fail-open/fail-closed DEFAULT_POLICY switch) and the per-method access
levels (read/write/readwrite/super), DELETE included.
"""
import pytest
from django.test import RequestFactory, override_settings

from django_resaas.core.middleware.front_end import FrontEndMiddleware
from django_resaas.models.front_end import FrontEnd

pytestmark = pytest.mark.django_db


def _run_middleware(request):
    def get_response(req):
        return "ok"

    return FrontEndMiddleware(get_response)(request)


def _request(path="/api/private/thing/", method="GET", frontend=None):
    factory = RequestFactory()
    kwargs = {}

    if frontend:
        kwargs["HTTP_FEK"] = frontend.fek
        kwargs["HTTP_FEP"] = frontend.fep

    return getattr(factory, method.lower())(path, **kwargs)


def _make_frontend(access):
    return FrontEnd.objects.create(
        name=f"{access}-frontend", fek=f"fek-{access}", fep=f"fep-{access}",
        access=access,
    )


BASE_FRONT_END = {
    "REQUIRE_CREDENTIALS": True,
    "PUBLIC_URL": ["public"],
    "URL_RULES": {
        "private": ["read", "write", "readwrite", "super"],
        "admin": ["write"],
    },
}


# =========================================================
# CREDENTIALS
# =========================================================

@override_settings(DJANGO_REST_AUTH={"FRONT_END": {**BASE_FRONT_END, "REQUIRE_CREDENTIALS": False}})
def test_credentials_not_required_when_disabled():
    response = _run_middleware(_request())
    assert response == "ok"


@override_settings(DJANGO_REST_AUTH={"FRONT_END": BASE_FRONT_END})
def test_missing_credentials_is_unauthorized():
    response = _run_middleware(_request())
    assert response.status_code == 401


@override_settings(DJANGO_REST_AUTH={"FRONT_END": BASE_FRONT_END})
def test_bad_credentials_is_unauthorized():
    fake = FrontEnd(fek="nope", fep="nope")  # not saved -> won't match DB
    response = _run_middleware(_request(frontend=fake))
    assert response.status_code == 401


# =========================================================
# URL SCOPE POLICY
# =========================================================

@override_settings(DJANGO_REST_AUTH={"FRONT_END": BASE_FRONT_END})
def test_known_scope_with_allowed_access_passes():
    frontend = _make_frontend("read")
    response = _run_middleware(_request("/api/private/thing/", frontend=frontend))
    assert response == "ok"


@override_settings(DJANGO_REST_AUTH={"FRONT_END": BASE_FRONT_END})
def test_known_scope_with_disallowed_access_is_forbidden():
    frontend = _make_frontend("write")
    response = _run_middleware(_request("/api/admin/thing/", frontend=frontend, method="GET"))
    assert response.status_code == 403


@override_settings(DJANGO_REST_AUTH={"FRONT_END": BASE_FRONT_END})
def test_unknown_scope_defaults_to_allow_for_backward_compatibility():
    frontend = _make_frontend("read")
    response = _run_middleware(_request("/api/some-unlisted-scope/thing/", frontend=frontend))
    assert response == "ok"


@override_settings(
    DJANGO_REST_AUTH={"FRONT_END": {**BASE_FRONT_END, "DEFAULT_POLICY": "deny"}}
)
def test_unknown_scope_is_forbidden_when_default_policy_is_deny():
    frontend = _make_frontend("super")
    response = _run_middleware(_request("/api/some-unlisted-scope/thing/", frontend=frontend))
    assert response.status_code == 403


@override_settings(
    DJANGO_REST_AUTH={"FRONT_END": {**BASE_FRONT_END, "DEFAULT_POLICY": "allow"}}
)
def test_unknown_scope_is_allowed_when_default_policy_is_explicitly_allow():
    frontend = _make_frontend("read")
    response = _run_middleware(_request("/api/some-unlisted-scope/thing/", frontend=frontend))
    assert response == "ok"


@override_settings(DJANGO_REST_AUTH={"FRONT_END": {}})
def test_absent_front_end_config_falls_back_to_defaults_and_still_allows_unknown_scope():
    # no URL_RULES / DEFAULT_POLICY configured at all - conf.py's DEFAULTS
    # kick in (REQUIRE_CREDENTIALS defaults to False, so no FEK/FEP needed)
    response = _run_middleware(_request("/api/whatever/thing/"))
    assert response == "ok"


# =========================================================
# METHOD PERMISSIONS
# =========================================================

@pytest.mark.parametrize(
    "access,method,allowed",
    [
        ("read", "GET", True),
        ("read", "POST", False),
        ("read", "DELETE", False),
        ("write", "POST", True),
        ("write", "DELETE", True),
        ("write", "GET", False),
        ("readwrite", "GET", True),
        ("readwrite", "POST", True),
        ("readwrite", "PUT", True),
        ("readwrite", "PATCH", True),
        ("readwrite", "DELETE", True),
        ("super", "DELETE", True),
        ("super", "GET", True),
    ],
)
@override_settings(DJANGO_REST_AUTH={"FRONT_END": BASE_FRONT_END})
def test_method_permission_matrix(access, method, allowed):
    frontend = _make_frontend(access)
    response = _run_middleware(
        _request("/api/private/thing/", method=method, frontend=frontend)
    )

    if allowed:
        assert response == "ok"
    else:
        assert response.status_code == 403

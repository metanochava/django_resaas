"""REST architecture guards (see CLAUDE.md, "REST API ARCHITECTURE").

They keep three rules true for every routed view, whoever adds it:

  1. every non-BaseAPIView endpoint is explicitly PUBLIC or PROTECTED
     (never public by omission - DRF's default here is "allow");
  2. a GET never changes state;
  3. the HTTP method of an endpoint matches what it does.
"""
import ast
import inspect
import textwrap

import pytest
from django.urls import get_resolver
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.test import APIClient

from django_resaas.saas.core.base.views import BaseAPIView

pytestmark = pytest.mark.django_db

# endpoints that are PUBLIC on purpose: the caller has no session yet. Anything
# else that is not a BaseAPIView must declare IsAuthenticated (or a stricter one).
PUBLIC_BY_DESIGN = {
    "LoginAPIView",
    "RegisterAPIView",
    "RequestRegisterOTPView",
    "RequestPasswordResetEmailAPIView",
    "PasswordTokenCheckAPIView",
    "SetNewPasswordAPIView",
    "ChangePasswordMobileAPIView",
    "ChangeTemporaryPasswordAPIView",
    "MailAPIView",
    "VerifyEmail",
    "SiteAPIView",
    "TokenRefreshView",
    "LoginTwoFactorAPIView",
    "LoginTwoFactorSetupAPIView",
    "LoginTwoFactorSetupConfirmAPIView",
}

# GET handlers that write only to a temp file / cache, never to the database
GET_WRITE_ALLOWLIST = {
    ("BranchAPIView", "qr"),          # renders a QR image through a temp file
    ("EntityAPIView", "qr"),
    ("LanguageAPIView", "translations"),  # fills the translations cache
}

WRITE_CALLS = {"save", "delete", "create", "bulk_create", "bulk_update", "get_or_create", "update_or_create", "hard_delete", "restore"}


def _routed_views():
    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                callback = pattern.callback
                view = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
                if view is not None:
                    yield prefix + str(pattern.pattern), view

    seen = {}
    for route, view in walk(get_resolver().url_patterns):
        seen.setdefault(view, route)
    return seen


def _declares_permissions(view):
    return any(
        "permission_classes" in vars(klass)
        and (klass.__module__.startswith("django_resaas") or klass.__name__ == "TokenRefreshView")
        or klass.__name__ == "TokenRefreshView"
        for klass in view.__mro__
    )


def _writes(function):
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    except (OSError, TypeError, SyntaxError):
        return []

    return sorted({
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_CALLS
    })


def _get_handlers(view):
    """(name, function) of every handler a GET can reach in `view`."""
    handlers = []

    if not issubclass(view, BaseAPIView) and hasattr(view, "get"):
        handlers.append(("get", view.get))

    for name in dir(view):
        method = getattr(view, name, None)
        metadata = getattr(method, "_resaas_action", None)
        if metadata and "get" in metadata["methods"]:
            handlers.append((name, method))

    return handlers


class TestExplicitClassification:

    def test_the_project_routes_views(self):
        assert len(_routed_views()) > 30

    def test_no_endpoint_is_public_by_omission(self):
        """Non-BaseAPIView endpoints must state PUBLIC or PROTECTED. BaseAPIView
        subclasses are protected by initial() (no permission -> 403)."""
        undeclared = sorted(
            f"{route}  ({view.__name__})"
            for view, route in _routed_views().items()
            if not issubclass(view, BaseAPIView)
            and view.__module__.startswith("django_resaas")
            and not _declares_permissions(view)
        )

        assert undeclared == [], (
            "These endpoints do not declare permission_classes, so DRF would leave them "
            "public. Declare IsAuthenticated (PROTECTED) or AllowAny (PUBLIC, and add the "
            "class to PUBLIC_BY_DESIGN):\n  " + "\n  ".join(undeclared)
        )

    def test_public_endpoints_are_exactly_the_documented_ones(self):
        public = {
            view.__name__
            for view in _routed_views()
            if not issubclass(view, BaseAPIView)
            and any(
                AllowAny in getattr(klass, "permission_classes", ())
                for klass in [view]
            )
        }
        public |= {"TokenRefreshView"}

        assert public - PUBLIC_BY_DESIGN == set(), "a new PUBLIC endpoint must be added to PUBLIC_BY_DESIGN deliberately"

    def test_protected_self_service_endpoints_reject_anonymous_callers(self):
        anonymous = APIClient()

        for method, path in (
            ("get", "/api/me/"),
            ("post", "/api/password/change/email/"),
            ("get", "/api/two_factor/"),
            ("get", "/api/sessions/"),
            ("get", "/api/security/activity/"),
            ("get", "/api/django_resaas/dashboards/"),
        ):
            response = getattr(anonymous, method)(path)
            assert response.status_code in (401, 403), (path, response.status_code)


class TestGetIsSafe:

    def test_no_get_handler_writes_to_the_database(self):
        offenders = []

        for view in _routed_views():
            for name, handler in _get_handlers(view):
                if (view.__name__, name) in GET_WRITE_ALLOWLIST:
                    continue
                writes = _writes(handler)
                if writes:
                    offenders.append(f"{view.__name__}.{name}: {writes}")

        assert offenders == [], "GET must never change state:\n  " + "\n  ".join(offenders)

    @pytest.mark.parametrize("path", ["/api/mail/", "/api/email/verify/"])
    def test_the_old_mutating_gets_are_gone(self, path):
        response = APIClient().get(path, {"email": "someone@example.com", "token": "x"})

        assert response.status_code == 405


class TestMethodMatchesOperation:

    def test_every_action_that_creates_or_removes_uses_a_mutating_method(self):
        """A resaas_action named like a write (add/remove/delete/create/...) must not be a GET."""
        verbs = ("add", "remove", "delete", "create", "assign", "approve", "reject", "confirm", "activate", "cancel", "submit", "toggle", "sync")
        offenders = []

        for view in _routed_views():
            for name in dir(view):
                metadata = getattr(getattr(view, name, None), "_resaas_action", None)
                if not metadata:
                    continue
                lowered = name.lower()
                if any(lowered.startswith(verb) for verb in verbs) and metadata["methods"] == ["get"]:
                    offenders.append(f"{view.__name__}.{name}")

        assert offenders == []


# ----------------------------------------------------------------- legacy viewsets

PROTECTED_COLLECTIONS = [
    "files", "translations", "themes", "layoutsettings", "branchusergroups", "branchusers",
    "entitytypes", "entitys", "branchs", "models", "apps", "resaasapps",
]


class TestLegacyViewSetsAreProtected:
    """These plain ModelViewSets used to answer anonymous callers (DRF's default
    here is "allow"): user/group assignments, permissions and groups of EVERY
    tenant were readable without signing in."""

    @pytest.mark.parametrize("name", PROTECTED_COLLECTIONS)
    def test_an_anonymous_list_is_refused(self, name, bootstrap_tenant):
        bootstrap_tenant("rest-anon-" + name)

        response = APIClient().get(f"/api/django_resaas/{name}/")

        assert response.status_code in (401, 403), (name, response.status_code)

    @pytest.mark.parametrize("path", ["/api/auth/groups/", "/api/auth/permissions/"])
    def test_anonymous_cannot_read_groups_or_permissions(self, path, bootstrap_tenant):
        bootstrap_tenant("rest-anon-auth")

        assert APIClient().get(path).status_code in (401, 403)

    def test_an_anonymous_write_is_refused_before_it_reaches_the_handler(self, bootstrap_tenant):
        tenant = bootstrap_tenant("rest-anon-write")
        anonymous = APIClient(raise_request_exception=False)

        assert anonymous.post("/api/django_resaas/branchs/", {"name": "x"}, format="json").status_code in (401, 403)
        assert anonymous.patch(f"/api/django_resaas/entitys/{tenant['entity'].id}/", {"name": "pwned"}, format="json").status_code in (401, 403)
        assert anonymous.delete(f"/api/django_resaas/branchs/{tenant['branch'].id}/").status_code in (401, 403)

    def test_the_language_list_stays_public_for_the_login_screen(self):
        assert APIClient().get("/api/django_resaas/languages/").status_code == 200

    def test_a_public_action_is_read_only(self):
        """public_actions is honoured for safe methods only."""
        response = APIClient().post("/api/django_resaas/languages/", {"name": "Klingon", "code": "tlh"}, format="json")

        assert response.status_code in (401, 403)

    def test_entity_type_branding_reads_stay_public_but_nothing_else_of_it(self, bootstrap_tenant):
        tenant = bootstrap_tenant("rest-branding")
        entity_type = tenant["entity"].entity_type
        anonymous = APIClient(raise_request_exception=False)

        assert anonymous.get(f"/api/django_resaas/entitytypes/{entity_type.id}/themeGet/").status_code == 200
        assert anonymous.get(f"/api/django_resaas/entitytypes/{entity_type.id}/models/").status_code in (401, 403)
        assert anonymous.get(f"/api/django_resaas/entitytypes/{entity_type.id}/groups/").status_code in (401, 403)
        assert anonymous.post(f"/api/django_resaas/entitytypes/{entity_type.id}/addApp/", {"id": 1}, format="json").status_code in (401, 403)

    def test_a_signed_in_caller_still_reaches_the_view(self, bootstrap_tenant):
        tenant = bootstrap_tenant("rest-signed-in")

        response = tenant["client"].get("/api/django_resaas/branchs/")

        assert response.status_code == 200


# ----------------------------------------------------------------- status codes

class TestForbiddenIsAn403:

    def test_a_missing_permission_on_a_base_view_is_403_not_400(self, bootstrap_tenant):
        """Covered end to end by test_cross_tenant_scope; here at the source."""
        from django.core.exceptions import ImproperlyConfigured  # noqa: F401
        import inspect as _inspect
        from django_resaas.saas.core.base import views

        source = _inspect.getsource(views.BaseAPIView.initial)

        assert 'fail(request, "Unauthorized", status=status.HTTP_403_FORBIDDEN)' in source


# ----------------------------------------------------------------- account endpoints

class TestPasswordChangeIsOwnAccount:

    def _user(self, name):
        from django_resaas.saas.models.user import User

        user = User.objects.create_user(username=name, email=f"{name}@rest.test", password="Own-Password-1")
        User.objects.filter(pk=user.pk).update(is_verified_email=True)
        return user

    def _client(self, user):
        client = APIClient(raise_request_exception=False)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {user.tokens()['access']}")
        return client

    def test_anonymous_cannot_probe_or_change_any_password(self):
        user = self._user("victim")

        response = APIClient().post(
            "/api/password/change/email/",
            {"email": user.email, "password": "Own-Password-1", "passwordNova": "Attacker-Pass-9"},
            format="json",
        )

        assert response.status_code in (401, 403)
        user.refresh_from_db()
        assert user.check_password("Own-Password-1")

    def test_a_signed_in_user_cannot_change_someone_elses_password(self):
        me, other = self._user("me"), self._user("other")

        response = self._client(me).post(
            "/api/password/change/email/",
            {"email": other.email, "password": "Own-Password-1", "passwordNova": "Attacker-Pass-9"},
            format="json",
        )

        assert response.status_code == 400
        other.refresh_from_db()
        assert other.check_password("Own-Password-1")

    def test_a_signed_in_user_changes_their_own_password(self):
        me = self._user("mine")

        response = self._client(me).post(
            "/api/password/change/email/",
            {"email": me.email, "password": "Own-Password-1", "passwordNova": "Brand-New-Pass-9"},
            format="json",
        )

        assert response.status_code == 202
        me.refresh_from_db()
        assert me.check_password("Brand-New-Pass-9")

    def test_the_wrong_current_password_is_refused(self):
        me = self._user("wrongpass")

        response = self._client(me).post(
            "/api/password/change/email/",
            {"email": me.email, "password": "Not-My-Password", "passwordNova": "Brand-New-Pass-9"},
            format="json",
        )

        assert response.status_code == 400
        me.refresh_from_db()
        assert me.check_password("Own-Password-1")


class TestStateChangingLinksArePost:

    def test_mail_is_post_only(self, monkeypatch):
        """mail/ (deprecated, superseded by password/reset/email/) used to SEND an
        e-mail on GET. It is POST only now. (Its link builder still reverses a URL
        name that does not exist, so it cannot send for a real account - kept only
        so an old caller gets a clear answer instead of a 404.)"""
        sent = []
        monkeypatch.setattr("django_resaas.saas.data.user.views.mail.EmailMultiAlternatives.send", lambda self, *a, **k: sent.append(self.to))
        client = APIClient()

        assert client.get("/api/mail/", {"email": "reset@rest.test"}).status_code == 405
        assert sent == []

        # POST reaches the handler: an unknown address gets the neutral answer
        assert client.post("/api/mail/", {"email": "nobody@rest.test"}, format="json").status_code == 200
        assert client.post("/api/mail/", {}, format="json").status_code == 400
        assert sent == []

    def test_verify_email_verifies_the_real_field_and_only_on_post(self):
        import jwt
        from django.conf import settings
        from django_resaas.saas.models.user import User

        user = User.objects.create_user(username="verify", email="verify@rest.test", password="Own-Password-1")
        token = jwt.encode({"user_id": str(user.id)}, settings.SECRET_KEY, algorithm="HS256")
        client = APIClient()

        assert client.get("/api/email/verify/", {"token": token}).status_code == 405
        user.refresh_from_db()
        assert user.is_verified_email is False

        assert client.post("/api/email/verify/", {"token": token}, format="json").status_code == 200
        user.refresh_from_db()
        assert user.is_verified_email is True

    def test_verify_email_rejects_a_bad_token(self):
        response = APIClient().post("/api/email/verify/", {"token": "not-a-token"}, format="json")

        assert response.status_code == 400

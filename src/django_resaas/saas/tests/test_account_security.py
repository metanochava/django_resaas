"""The signed-in user's own security overview: password_changed_at, active
sessions (and ending them), recent activity - plus the legacy UserAPIView
actions that used to answer anonymous requests."""
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from django_resaas.saas.core.services import session_service
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.user import User
from django_resaas.saas.models.user_login import UserLogin

pytestmark = pytest.mark.django_db

CHROME_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
FIREFOX_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"

PERMISSION_CHECK = "django_resaas.saas.data.user.views.user.isPermited"


def _account(username="ana"):
    user = User.objects.create_user(username=username, email=f"{username}@acct.test", password="Own-Password-1")
    User.objects.filter(pk=user.pk).update(is_verified_email=True)
    return user


def _sign_in(user, agent=CHROME_MAC, password="Own-Password-1"):
    """A real sign-in through the API; returns an authenticated client."""
    response = APIClient().post(
        "/api/login/", {"identifier": user.username, "password": password}, format="json", HTTP_USER_AGENT=agent
    )
    assert response.status_code == 200, response.data

    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['tokens']['access']}")
    client.refresh = response.data["tokens"]["refresh"]
    return client


# ------------------------------------------------------------ password_changed_at

class TestPasswordChangedAt:

    def test_it_is_set_when_the_user_changes_their_password(self):
        user = _account()
        before = timezone.now()

        user.set_password("Another-Password-2")
        user.save(update_fields=["password"])

        user.refresh_from_db()
        assert user.password_changed_at and user.password_changed_at >= before

    def test_it_is_not_set_while_a_temporary_password_is_issued(self):
        from django_resaas.saas.core.services import temporary_password_service as service

        user = _account("issued")
        User.objects.filter(pk=user.pk).update(password_changed_at=None)
        user.refresh_from_db()

        service.issue(user)

        user.refresh_from_db()
        assert user.password_changed_at is None

    def test_it_is_set_when_the_temporary_password_is_replaced(self):
        from django_resaas.saas.core.services import temporary_password_service as service

        user = _account("replaced")
        service.issue(user)
        service.complete(user, "Chosen-Password-3")

        user.refresh_from_db()
        assert user.password_changed_at

    def test_me_reports_it(self, bootstrap_tenant):
        tenant = bootstrap_tenant("acct-me")
        tenant["user"].set_password("Changed-Pass-9")
        tenant["user"].save(update_fields=["password"])

        response = tenant["client"].get("/api/me/")

        assert response.data["password_changed_at"]


# ------------------------------------------------------------ sessions

class TestSessions:

    def test_every_sign_in_is_recorded_with_its_device_and_session(self):
        user = _account()
        _sign_in(user, CHROME_MAC)

        login = UserLogin.objects.get(user=user)
        assert login.dispositivo == "Chrome · macOS"
        assert login.token_jti

    def test_device_names_come_from_the_user_agent_only(self):
        assert session_service.describe_device(CHROME_MAC) == "Chrome · macOS"
        assert session_service.describe_device(FIREFOX_WIN) == "Firefox · Windows"
        assert session_service.describe_device(IPHONE) == "Safari · iOS"
        assert session_service.describe_device("") == ""

    def test_lists_only_my_active_sessions_and_marks_the_current_one(self):
        user = _account()
        other = _account("other")
        first = _sign_in(user, FIREFOX_WIN)
        second = _sign_in(user, CHROME_MAC)
        _sign_in(other)

        rows = second.get("/api/sessions/").data["data"]

        assert [row["device"] for row in rows] == ["Chrome · macOS", "Firefox · Windows"]
        assert [row["current"] for row in rows] == [True, False]
        assert all("ip" not in row and "location" not in row for row in rows)
        # from the other device the flag flips
        assert [row["current"] for row in first.get("/api/sessions/").data["data"]] == [False, True]

    def test_a_terminated_session_can_no_longer_refresh(self):
        user = _account()
        old = _sign_in(user, FIREFOX_WIN)
        current = _sign_in(user, CHROME_MAC)
        target = next(row for row in current.get("/api/sessions/").data["data"] if not row["current"])

        response = current.post(f"/api/sessions/{target['id']}/terminate/")

        assert response.status_code == 200
        assert [row["current"] for row in current.get("/api/sessions/").data["data"]] == [True]
        refreshed = APIClient(raise_request_exception=False).post("/api/refresh_token/", {"refresh": old.refresh}, format="json")
        assert refreshed.status_code == 401

    def test_you_cannot_terminate_the_current_session_here(self):
        user = _account()
        client = _sign_in(user)
        current = client.get("/api/sessions/").data["data"][0]

        response = client.post(f"/api/sessions/{current['id']}/terminate/")

        assert response.status_code == 400 and response.data["code"] == "cannot_terminate_current_session"

    def test_you_cannot_terminate_someone_elses_session(self):
        mine, theirs = _account("mine"), _account("theirs")
        mine_client = _sign_in(mine)
        their_client = _sign_in(theirs)
        their_id = their_client.get("/api/sessions/").data["data"][0]["id"]

        response = mine_client.post(f"/api/sessions/{their_id}/terminate/")

        assert response.status_code == 404
        assert len(their_client.get("/api/sessions/").data["data"]) == 1

    def test_terminate_others_keeps_only_the_current_session(self):
        user = _account()
        _sign_in(user, FIREFOX_WIN)
        _sign_in(user, IPHONE)
        current = _sign_in(user, CHROME_MAC)

        response = current.post("/api/sessions/terminate_others/")

        assert response.status_code == 200 and response.data["count"] == 2
        rows = current.get("/api/sessions/").data["data"]
        assert len(rows) == 1 and rows[0]["current"] is True

    def test_terminate_others_never_touches_another_users_sessions(self):
        user, other = _account("keeper"), _account("bystander")
        bystander = _sign_in(other)
        _sign_in(user)
        current = _sign_in(user)

        current.post("/api/sessions/terminate_others/")

        assert len(bystander.get("/api/sessions/").data["data"]) == 1

    def test_a_token_without_a_session_id_cannot_manage_other_sessions(self):
        user = _account()
        client = _sign_in(user)

        with mock.patch("django_resaas.saas.data.user.views.account_security.session_service.current_session_id", return_value=None):
            response = client.post("/api/sessions/terminate_others/")

        assert response.status_code == 409 and response.data["code"] == "current_session_unknown"

    def test_sessions_need_authentication(self):
        anonymous = APIClient(raise_request_exception=False)

        assert anonymous.get("/api/sessions/").status_code in (401, 403)
        assert anonymous.post("/api/sessions/terminate_others/").status_code in (401, 403)
        assert anonymous.post("/api/sessions/abc/terminate/").status_code in (401, 403)


# ------------------------------------------------------------ activity

class TestActivity:

    def test_lists_my_sign_ins_and_my_own_account_changes_newest_first(self):
        user = _account()
        client = _sign_in(user)
        user.set_password("Changed-Password-4")
        user.save(update_fields=["password"])

        types = [event["type"] for event in client.get("/api/security/activity/").data["data"]]

        assert types == ["PASSWORD_CHANGED", "login"]

    def test_email_and_phone_changes_are_recorded(self, bootstrap_tenant):
        tenant = bootstrap_tenant("acct-contact")

        with mock.patch("django_resaas.saas.data.user.views.profile_contact_otp.verify_registration_otp", return_value=True):
            tenant["client"].post("/api/profile/contact/otp/confirm/", {"channel": "email", "identifier": "new@acct.test", "otp": "123456"}, format="json")
            tenant["client"].post("/api/profile/contact/otp/confirm/", {"channel": "mobile", "identifier": "+258841111111", "otp": "123456"}, format="json")

        actions = set(AuditLog.objects.filter(user=tenant["user"]).values_list("action", flat=True))
        assert {"EMAIL_CHANGED", "MOBILE_CHANGED"} <= actions

    def test_it_never_shows_an_administrators_actions_on_my_account(self):
        user = _account()
        client = _sign_in(user)
        AuditLog.objects.create(action="TEMPORARY_PASSWORD_VIEWED", model="User", object_id=str(user.pk))

        types = [event["type"] for event in client.get("/api/security/activity/").data["data"]]

        assert "TEMPORARY_PASSWORD_VIEWED" not in types

    def test_it_never_shows_another_users_events(self):
        mine, theirs = _account("me"), _account("them")
        client = _sign_in(mine)
        _sign_in(theirs)
        AuditLog.objects.create(action="PASSWORD_CHANGED", model="User", object_id=str(theirs.pk))

        events = client.get("/api/security/activity/").data["data"]

        assert [event["type"] for event in events] == ["login"]

    def test_a_brand_new_account_has_no_password_change_event(self):
        user = _account("brandnew")

        assert not AuditLog.objects.filter(action="PASSWORD_CHANGED", object_id=str(user.pk)).exists()

    def test_the_old_logins_endpoint_now_works_and_is_own_data_only(self):
        user, other = _account("logins"), _account("stranger")
        client = _sign_in(user, FIREFOX_WIN)
        _sign_in(other)

        response = client.get("/api/logins/")

        assert response.status_code == 200
        assert [row["device"] for row in response.data["data"]] == ["Firefox · Windows"]


# ------------------------------------------------------------ legacy UserAPIView actions

DETAIL_GET = ("userEntitys", "userBranchs", "userPerson", "permissions", "logins", "userGroups")
DETAIL_POST = ("addUserBranch", "removeUserBranch", "addGroup", "removeGroup")


def _url(user, action):
    return f"/api/django_resaas/users/{user.id}/{action}/"


class TestLegacyUserActionsAreNotOpen:

    @pytest.mark.parametrize("action", DETAIL_GET)
    def test_anonymous_gets_are_refused(self, action):
        user = _account()

        assert APIClient(raise_request_exception=False).get(_url(user, action)).status_code in (401, 403)

    @pytest.mark.parametrize("action", DETAIL_POST)
    def test_anonymous_posts_are_refused(self, action):
        user = _account()

        assert APIClient(raise_request_exception=False).post(_url(user, action), {}, format="json").status_code in (401, 403)

    def test_the_list_and_detail_endpoints_need_a_session_too(self):
        user = _account()
        anonymous = APIClient(raise_request_exception=False)

        assert anonymous.get("/api/django_resaas/users/").status_code in (401, 403)
        assert anonymous.get(f"/api/django_resaas/users/{user.id}/").status_code in (401, 403)

    def test_a_user_can_read_their_own_data_without_any_permission(self, bootstrap_tenant):
        tenant = bootstrap_tenant("legacy-self")

        with mock.patch(PERMISSION_CHECK, return_value=False):
            for action in ("userPerson", "userBranchs", "permissions", "logins", "userEntitys"):
                assert tenant["client"].get(_url(tenant["user"], action)).status_code == 200, action

    def test_another_users_data_needs_view_user_and_the_same_entity(self, bootstrap_tenant):
        mine = bootstrap_tenant("legacy-a")
        theirs = bootstrap_tenant("legacy-b")
        client = mine["client"]
        client.raise_request_exception = False

        with mock.patch(PERMISSION_CHECK, return_value=False):
            denied = client.get(_url(theirs["user"], "userPerson"))
        cross = client.get(_url(theirs["user"], "userPerson"))

        assert denied.status_code == 403
        assert cross.status_code == 404

    def test_a_member_of_my_entity_is_visible_with_the_permission(self, bootstrap_tenant):
        tenant = bootstrap_tenant("legacy-member")
        member = _account("member")
        EntityUser.objects.get_or_create(user=member, entity=tenant["entity"])

        assert tenant["client"].get(_url(member, "userPerson")).status_code == 200

    def test_changing_a_users_branches_needs_change_user_even_for_yourself(self, bootstrap_tenant):
        tenant = bootstrap_tenant("legacy-branch")
        other_branch = Branch.objects.create(name="Second", entity=tenant["entity"])
        client = tenant["client"]
        client.raise_request_exception = False

        with mock.patch(PERMISSION_CHECK, return_value=False):
            denied = client.post(_url(tenant["user"], "addUserBranch"), {"branch": str(other_branch.id)}, format="json")

        assert denied.status_code == 403
        assert not BranchUser.objects.filter(user=tenant["user"], branch=other_branch).exists()

    def test_a_branch_of_another_entity_cannot_be_added(self, bootstrap_tenant):
        mine = bootstrap_tenant("legacy-cross-a")
        theirs = bootstrap_tenant("legacy-cross-b")
        client = mine["client"]
        client.raise_request_exception = False

        response = client.post(_url(mine["user"], "addUserBranch"), {"branch": str(theirs["branch"].id)}, format="json")

        assert response.status_code == 404
        assert not BranchUser.objects.filter(user=mine["user"], branch=theirs["branch"]).exists()

    def test_an_authorised_admin_can_add_and_remove_a_branch_of_their_entity(self, bootstrap_tenant):
        tenant = bootstrap_tenant("legacy-admin")
        member = _account("brancher")
        EntityUser.objects.get_or_create(user=member, entity=tenant["entity"])
        second = Branch.objects.create(name="Second", entity=tenant["entity"])

        added = tenant["client"].post(_url(member, "addUserBranch"), {"branch": str(second.id)}, format="json")
        assert added.status_code == 201 and BranchUser.objects.filter(user=member, branch=second).exists()

        removed = tenant["client"].post(_url(member, "removeUserBranch"), {"branch": str(second.id)}, format="json")
        assert removed.status_code == 200 and not BranchUser.objects.filter(user=member, branch=second).exists()

    def test_removing_a_branch_that_is_not_there_is_a_404_not_a_crash(self, bootstrap_tenant):
        tenant = bootstrap_tenant("legacy-missing")
        member = _account("nobranch")
        EntityUser.objects.get_or_create(user=member, entity=tenant["entity"])
        second = Branch.objects.create(name="Second", entity=tenant["entity"])
        tenant["client"].raise_request_exception = False

        response = tenant["client"].post(_url(member, "removeUserBranch"), {"branch": str(second.id)}, format="json")

        assert response.status_code == 404

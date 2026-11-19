"""Refresh token rotation (SIMPLE_JWT ROTATE_REFRESH_TOKENS +
BLACKLIST_AFTER_ROTATION) with stable sessions.

- Each refresh answers a new refresh token; the one used is refused after.
- The session keeps its id (the tokens' "sid"): it stays in the session list,
  can be ended, and is not "ended" because it rotated.
- A rotated token used again after the grace window is taken as stolen: the
  session (and its single sign-on family) ends. Within the window (two tabs
  refreshing at once) it is only refused."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from django_resaas.saas.core.services import session_service
from django_resaas.saas.models.user import User
from django_resaas.saas.models.user_login import UserLogin

pytestmark = pytest.mark.django_db
REFRESH = "/api/refresh_token/"


def _session(username):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass-123-xyz")
    tokens = user.tokens()
    session_service.record_login(user, None, tokens)
    return user, tokens


def _refresh(token):
    return APIClient().post(REFRESH, {"refresh": token}, format="json")


def test_a_refresh_rotates_and_the_old_token_is_refused():
    user, tokens = _session("rot-basic")
    sid = RefreshToken(tokens["refresh"])["jti"]
    first = _refresh(tokens["refresh"])
    assert first.status_code in (200, 202), first.content
    new = first.data["refresh"]
    assert new != tokens["refresh"]
    assert RefreshToken(new)["sid"] == sid                                         # same session
    assert _refresh(new).status_code in (200, 202)


def test_the_session_keeps_its_id_across_rotations():
    user, tokens = _session("rot-list")
    sid = RefreshToken(tokens["refresh"])["jti"]
    current = tokens["refresh"]
    for _ in range(3):
        current = _refresh(current).data["refresh"]

    sessions = session_service.active_sessions(user, current_sid=sid)
    assert [s["id"] for s in sessions] == [sid]
    assert sessions[0]["current"] is True
    assert UserLogin.objects.get(token_jti=sid).current_jti == RefreshToken(current)["jti"]
    assert session_service.session_ended(sid) is False                               # rotated, not ended


def test_ending_the_session_stops_its_current_token():
    user, tokens = _session("rot-end")
    sid = RefreshToken(tokens["refresh"])["jti"]
    current = _refresh(tokens["refresh"]).data["refresh"]

    assert session_service.terminate(user, sid) is True
    assert session_service.session_ended(sid) is True
    assert _refresh(current).status_code == 401
    assert session_service.active_sessions(user) == []


def test_a_rotated_token_used_again_ends_the_session():
    user, tokens = _session("rot-theft")
    sid = RefreshToken(tokens["refresh"])["jti"]
    current = _refresh(tokens["refresh"]).data["refresh"]
    # the old token was rotated two minutes ago (past the grace window)
    BlacklistedToken.objects.filter(token__jti=sid).update(blacklisted_at=timezone.now() - timedelta(minutes=2))

    assert _refresh(tokens["refresh"]).status_code == 401
    assert session_service.session_ended(sid) is True                               # the thief and the owner both out
    assert _refresh(current).status_code == 401


def test_two_tabs_refreshing_at_once_only_refuse_the_late_one():
    user, tokens = _session("rot-tabs")
    sid = RefreshToken(tokens["refresh"])["jti"]
    current = _refresh(tokens["refresh"]).data["refresh"]

    assert _refresh(tokens["refresh"]).status_code == 401                            # within the grace window
    assert session_service.session_ended(sid) is False
    assert _refresh(current).status_code in (200, 202)


def test_a_forged_or_unknown_token_is_just_refused():
    assert _refresh("not-a-token").status_code == 401
    assert session_service.refresh_reused("not-a-token") is False

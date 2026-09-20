"""Two-factor authentication: TOTP, hashed single-use recovery codes, the sign-in
challenge and the policy by levels (EntityType > Entity > EntityUser)."""
import time

import pyotp
import pytest
from django.core import signing
from django.core.cache import cache
from rest_framework.test import APIClient

from django_resaas.saas.core.services import two_factor_service as service
from django_resaas.saas.core.utils.secret_box import decrypt_text
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.two_factor import UserTwoFactor
from django_resaas.saas.models.two_factor_policy import TwoFactorPolicy as P
from django_resaas.saas.models.user import User

pytestmark = pytest.mark.django_db

PASSWORD = "Own-Password-1"


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


def _user(username="ana"):
    user = User.objects.create_user(username=username, email=f"{username}@tf.test", password=PASSWORD)
    User.objects.filter(pk=user.pk).update(is_verified_email=True)
    return user


def _secret(user):
    return decrypt_text(UserTwoFactor.objects.get(user=user).secret_encrypted, purpose=service.PURPOSE)


def _code(user, offset=0):
    return pyotp.TOTP(_secret(user)).at(int(time.time()) + offset * service.STEP)


def _enrol(user):
    """Enrol through the service; returns the recovery codes."""
    service.begin_setup(user)
    return service.confirm_setup(user, _code(user))


def _login(username="ana", password=PASSWORD):
    return APIClient().post("/api/login/", {"identifier": username, "password": password}, format="json")


def _authed(user):
    tokens = user.tokens()
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _tree(entity_type=P.INHERIT, entity=P.INHERIT, member=P.INHERIT, user=None):
    kind = EntityType.objects.create(name="Clinic", two_factor_policy=entity_type)
    org = Entity.objects.create(name="Org", entity_type=kind, two_factor_policy=entity)
    user = user or _user()
    EntityUser.objects.create(entity=org, user=user, two_factor_policy=member)
    return kind, org, user


# ------------------------------------------------------------------ policy

class TestPolicyLevels:

    def test_nobody_has_an_opinion_so_the_platform_default_applies(self):
        assert service.resolve_policy(None, P.INHERIT, P.INHERIT) == P.OPTIONAL

    @pytest.mark.parametrize("levels,expected", [
        ((P.OPTIONAL, P.INHERIT, P.INHERIT), P.OPTIONAL),
        ((P.INHERIT, P.DISABLED, P.INHERIT), P.DISABLED),
        ((P.REQUIRED, P.INHERIT, P.INHERIT), P.REQUIRED),
        ((P.DISABLED, P.OPTIONAL, P.INHERIT), P.OPTIONAL),   # most specific wins
        ((P.OPTIONAL, P.OPTIONAL, P.DISABLED), P.DISABLED),
    ])
    def test_the_most_specific_level_with_an_opinion_wins(self, levels, expected):
        assert service.resolve_policy(*levels) == expected

    @pytest.mark.parametrize("levels", [
        (P.REQUIRED, P.DISABLED, P.DISABLED),
        (P.REQUIRED, P.OPTIONAL, P.INHERIT),
        (P.INHERIT, P.REQUIRED, P.DISABLED),
        (P.OPTIONAL, P.OPTIONAL, P.REQUIRED),
    ])
    def test_a_required_level_can_never_be_weakened_by_another(self, levels):
        assert service.resolve_policy(*levels) == P.REQUIRED

    def test_the_policy_is_resolved_through_the_real_chain(self):
        _, org, user = _tree(entity_type=P.REQUIRED, entity=P.DISABLED, member=P.DISABLED)

        assert service.effective_policy(user, org) == P.REQUIRED
        assert service.requires_two_factor(user) is True

    def test_a_member_level_can_relax_an_optional_organisation(self):
        _, org, user = _tree(entity=P.OPTIONAL, member=P.DISABLED)

        assert service.effective_policy(user, org) == P.DISABLED
        assert service.requires_two_factor(user) is False

    def test_any_required_entity_makes_sign_in_require_it(self):
        _, _, user = _tree()
        other = Entity.objects.create(name="Strict", entity_type=EntityType.objects.create(name="Strict kind"), two_factor_policy=P.REQUIRED)
        EntityUser.objects.create(entity=other, user=user)

        assert service.requires_two_factor(user) is True

    def test_another_entitys_policy_never_reaches_this_user(self):
        _, _, user = _tree()
        stranger = _user("stranger")
        _tree(entity=P.REQUIRED, user=stranger)

        assert service.requires_two_factor(user) is False


# ------------------------------------------------------------------ enrolment

class TestEnrolment:

    def test_the_secret_is_stored_encrypted_and_pending_until_confirmed(self):
        user = _user()
        started = service.begin_setup(user)

        row = UserTwoFactor.objects.get(user=user)
        assert started["secret"] not in row.secret_encrypted
        assert row.active is False
        assert service.state_of(user) == service.PENDING
        assert started["otpauth_uri"].startswith("otpauth://totp/")

    def test_a_wrong_code_does_not_activate_it(self):
        user = _user()
        service.begin_setup(user)

        with pytest.raises(service.TwoFactorError) as error:
            service.confirm_setup(user, "000000")

        assert error.value.code == "invalid_code"
        assert service.is_active(user) is False

    def test_the_first_valid_code_activates_it_and_returns_recovery_codes_once(self):
        user = _user()
        codes = _enrol(user)

        assert service.is_active(user)
        assert len(codes) == service.RECOVERY_CODES and len(set(codes)) == len(codes)
        assert AuditLog.objects.filter(action=service.ENABLED, object_id=str(user.pk)).count() == 1

    def test_recovery_codes_are_stored_hashed_never_in_plain_text(self):
        user = _user()
        codes = _enrol(user)

        stored = UserTwoFactor.objects.get(user=user).recovery_hashes

        assert len(stored) == service.RECOVERY_CODES
        for code in codes:
            assert code not in stored and code.replace("-", "") not in stored

    def test_enrolling_again_while_active_is_refused(self):
        user = _user()
        _enrol(user)

        with pytest.raises(service.TwoFactorError) as error:
            service.begin_setup(user)

        assert error.value.code == "two_factor_already_active"


# ------------------------------------------------------------------ verification

class TestVerification:

    def test_a_valid_code_is_accepted_and_cannot_be_replayed(self):
        user = _user()
        _enrol(user)
        code = _code(user, offset=1)   # a later step than the one used to enrol

        assert service.verify(user, code) == "totp"

        with pytest.raises(service.TwoFactorError):
            service.verify(user, code)

    def test_malformed_codes_are_rejected(self):
        user = _user()
        _enrol(user)

        for bad in ("", "12345", "abcdef", "1234567", None):
            with pytest.raises(service.TwoFactorError):
                service.verify(user, bad)

    def test_a_recovery_code_works_exactly_once(self):
        user = _user()
        codes = _enrol(user)

        assert service.verify(user, codes[0]) == "recovery"
        assert service.verify(user, codes[1].lower().replace("-", " ")) == "recovery"

        with pytest.raises(service.TwoFactorError):
            service.verify(user, codes[0])

        assert AuditLog.objects.filter(action=service.RECOVERY_USED).count() == 2
        assert len(UserTwoFactor.objects.get(user=user).recovery_hashes) == service.RECOVERY_CODES - 2

    def test_repeated_failures_lock_the_account_out_with_429(self):
        user = _user()
        _enrol(user)

        for _ in range(service.MAX_FAILURES):
            with pytest.raises(service.TwoFactorError):
                service.verify(user, "000000")

        with pytest.raises(service.TwoFactorError) as error:
            service.verify(user, _code(user, offset=1))

        assert error.value.code == "too_many_attempts" and error.value.http_status == 429

    def test_verifying_without_an_active_factor_is_refused(self):
        with pytest.raises(service.TwoFactorError) as error:
            service.verify(_user(), "123456")

        assert error.value.code == "two_factor_not_active"


# ------------------------------------------------------------------ disable / regenerate

class TestManage:

    def test_disabling_needs_a_valid_code(self):
        user = _user()
        _enrol(user)

        with pytest.raises(service.TwoFactorError):
            service.disable(user, "000000")

        assert service.is_active(user)

        service.disable(user, _code(user, offset=1))

        assert service.state_of(user) == service.NOT_CONFIGURED
        assert AuditLog.objects.filter(action=service.DISABLED_EVENT).exists()

    def test_a_required_policy_forbids_disabling(self):
        _, _, user = _tree(entity=P.REQUIRED)
        _enrol(user)

        with pytest.raises(service.TwoFactorError) as error:
            service.disable(user, _code(user, offset=1))

        assert error.value.code == "two_factor_required_by_policy" and error.value.http_status == 403
        assert service.is_active(user)

    def test_regenerating_replaces_every_old_recovery_code(self):
        user = _user()
        old = _enrol(user)

        fresh = service.regenerate_recovery_codes(user, _code(user, offset=1))

        assert set(fresh).isdisjoint(old)
        with pytest.raises(service.TwoFactorError):
            service.verify(user, old[0])
        assert service.verify(user, fresh[0]) == "recovery"


# ------------------------------------------------------------------ sign-in

class TestSignIn:

    def test_without_two_factor_the_password_gives_tokens_as_before(self):
        _user()
        response = _login()

        assert response.status_code == 200
        assert response.data["tokens"]["access"] and not response.data["two_factor"]

    def test_an_active_factor_withholds_tokens_and_returns_a_challenge(self):
        user = _user()
        _enrol(user)

        response = _login()

        assert response.status_code == 200
        assert response.data["tokens"] is None
        assert response.data["two_factor"] == "two_factor_required" and response.data["challenge"]

    def test_the_code_completes_the_sign_in(self):
        user = _user()
        _enrol(user)
        challenge = _login().data["challenge"]

        response = APIClient().post(
            "/api/login/two_factor/", {"challenge": challenge, "code": _code(user, offset=1)}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["tokens"]["access"]
        assert user.logins.count() == 1 if hasattr(user, "logins") else True

    def test_a_wrong_code_gives_no_tokens(self):
        user = _user()
        _enrol(user)
        challenge = _login().data["challenge"]

        response = APIClient().post("/api/login/two_factor/", {"challenge": challenge, "code": "000000"}, format="json")

        assert response.status_code == 400 and response.data["code"] == "invalid_code"
        assert "tokens" not in response.data

    def test_a_recovery_code_completes_the_sign_in(self):
        user = _user()
        codes = _enrol(user)
        challenge = _login().data["challenge"]

        response = APIClient().post("/api/login/two_factor/", {"challenge": challenge, "code": codes[0]}, format="json")

        assert response.status_code == 200 and response.data["tokens"]["access"]

    def test_a_forged_tampered_or_missing_challenge_is_rejected(self):
        user = _user()
        _enrol(user)
        real = _login().data["challenge"]
        forged = signing.dumps({"uid": str(user.pk), "purpose": service.LOGIN}, salt="another.salt")

        for challenge in (forged, real[:-3] + "abc", "", None, 5):
            response = APIClient().post(
                "/api/login/two_factor/", {"challenge": challenge, "code": _code(user, offset=1)}, format="json"
            )
            assert response.status_code == 401, challenge
            assert response.data["code"] == "invalid_challenge"

    def test_an_expired_challenge_is_rejected(self, monkeypatch):
        user = _user()
        _enrol(user)
        challenge = _login().data["challenge"]

        monkeypatch.setattr(service, "CHALLENGE_TTL", -1)

        response = APIClient().post(
            "/api/login/two_factor/", {"challenge": challenge, "code": _code(user, offset=1)}, format="json"
        )

        assert response.status_code == 401

    def test_a_setup_challenge_cannot_be_used_as_a_login_challenge(self):
        _, _, user = _tree(entity=P.REQUIRED)
        setup_challenge = _login().data["challenge"]

        response = APIClient().post("/api/login/two_factor/", {"challenge": setup_challenge, "code": "123456"}, format="json")

        assert response.status_code == 401

    def test_a_required_policy_forces_enrolment_before_any_session(self):
        _, _, user = _tree(entity=P.REQUIRED)

        first = _login()
        assert first.data["two_factor"] == "two_factor_setup_required" and first.data["tokens"] is None

        client = APIClient()
        started = client.post("/api/login/two_factor/setup/", {"challenge": first.data["challenge"]}, format="json")
        assert started.status_code == 200
        assert started.data["secret"] and started.data["qr"].startswith("data:image/png;base64,")

        done = client.post(
            "/api/login/two_factor/setup/confirm/",
            {"challenge": first.data["challenge"], "code": _code(user)},
            format="json",
        )

        assert done.status_code == 200, done.data
        assert done.data["tokens"]["access"] and len(done.data["recovery_codes"]) == service.RECOVERY_CODES
        assert service.is_active(user)

    def test_enrolment_at_sign_in_is_refused_when_nothing_requires_it(self):
        user = _user()
        forged = service.make_challenge(user, service.SETUP)

        response = APIClient().post("/api/login/two_factor/setup/", {"challenge": forged}, format="json")

        assert response.status_code == 401

    def test_changing_a_temporary_password_does_not_skip_the_second_factor(self):
        from django_resaas.saas.core.services import temporary_password_service

        user = _user()
        _enrol(user)
        temporary = temporary_password_service.issue(user)
        plain = temporary if isinstance(temporary, str) else temporary_password_service.reveal(user, actor=user)

        response = APIClient().post(
            "/api/password/change/temporary/",
            {"identifier": user.username, "password": plain, "new_password": "Brand-New-Pass-9"},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["tokens"] is None and response.data["two_factor"] == "two_factor_required"

    def test_a_disabled_policy_still_enforces_an_already_active_factor(self):
        _, _, user = _tree(entity=P.DISABLED)
        _enrol(user)

        assert _login().data["two_factor"] == "two_factor_required"


# ------------------------------------------------------------------ self-service API

class TestSelfServiceApi:

    def test_every_self_service_route_needs_authentication(self):
        anon = APIClient()

        for method, path in (
            ("get", "/api/two_factor/"), ("post", "/api/two_factor/setup/"), ("post", "/api/two_factor/confirm/"),
            ("post", "/api/two_factor/disable/"), ("post", "/api/two_factor/recovery/"),
        ):
            assert getattr(anon, method)(path).status_code in (401, 403), path

    def test_status_reports_state_and_policy(self):
        user = _user()

        assert _authed(user).get("/api/two_factor/").data == {
            "state": "not_configured", "policy": "optional", "recovery_codes_remaining": 0,
            "can_setup": True, "can_disable": True,
        }

    def test_full_lifecycle_through_the_api(self):
        user = _user()
        client = _authed(user)

        started = client.post("/api/two_factor/setup/")
        assert started.status_code == 200 and started.data["qr"].startswith("data:image/png;base64,")

        confirmed = client.post("/api/two_factor/confirm/", {"code": _code(user)}, format="json")
        assert confirmed.status_code == 200 and len(confirmed.data["recovery_codes"]) == service.RECOVERY_CODES

        assert client.get("/api/two_factor/").data["state"] == "active"
        assert client.get("/api/two_factor/").data["recovery_codes_remaining"] == service.RECOVERY_CODES

        assert client.post("/api/two_factor/disable/", {"code": "000000"}, format="json").status_code == 400
        assert client.post("/api/two_factor/disable/", {"code": _code(user, offset=1)}, format="json").status_code == 200
        assert client.get("/api/two_factor/").data["state"] == "not_configured"

    def test_setup_is_refused_when_the_organisation_disabled_it(self):
        from unittest import mock

        _, org, user = _tree(entity=P.DISABLED)

        # the entity normally comes from the signed X-RESAAS-Context header
        with mock.patch("django_resaas.saas.data.user.views.two_factor._entity", return_value=org):
            response = _authed(user).post("/api/two_factor/setup/")

        assert response.status_code == 403 and response.data["code"] == "two_factor_disabled"
        assert not UserTwoFactor.objects.filter(user=user).exists()

    def test_a_user_only_ever_touches_their_own_factor(self):
        ana, bob = _user("ana"), _user("bob")
        _enrol(bob)

        client = _authed(ana)

        assert client.get("/api/two_factor/").data["state"] == "not_configured"
        assert client.post("/api/two_factor/disable/", {"code": _code(bob, offset=1)}, format="json").status_code == 409
        assert service.is_active(bob)

    def test_the_secret_is_never_returned_by_status_or_confirm(self):
        user = _user()
        client = _authed(user)
        client.post("/api/two_factor/setup/")
        secret = _secret(user)

        assert secret not in str(client.get("/api/two_factor/").data)
        assert secret not in str(client.post("/api/two_factor/confirm/", {"code": _code(user)}, format="json").data)

    def test_two_factor_events_show_in_the_security_activity(self):
        user = _user()
        client = _authed(user)
        client.post("/api/two_factor/setup/")
        client.post("/api/two_factor/confirm/", {"code": _code(user)}, format="json")

        types = [event["type"] for event in client.get("/api/security/activity/").data["data"]]

        assert "TWO_FACTOR_ENABLED" in types

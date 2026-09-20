"""TEMPORARY password lifecycle.

  TEMPORARY  hash + audited, encrypted copy an authorised administrator can
             read back; must be replaced at the first login; expires
  EXPIRED    login refused, nothing revealed, only a new one can be issued
  PERMANENT  the user's own choice: no recoverable copy exists, ever

Tenant scope AND the specific permission must both pass; the plaintext never
reaches the serializer, the logs, the audit or the database."""
import logging
from datetime import timedelta
from unittest import mock

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from django_resaas.saas.core.services import temporary_password_service as service
from django_resaas.saas.core.utils.secret_box import SecretBoxError, decrypt_text, encrypt_text
from django_resaas.saas.data.user.serializers.user import UserSerializer
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.person import Person
from django_resaas.saas.models.user import User
from django_resaas.saas.models.user_temporary_password import UserTemporaryPassword

pytestmark = pytest.mark.django_db

PERMISSION_CHECK = "django_resaas.saas.data.user.views.user.isPermited"


def _member(tenant, username="staff", email=None):
    user = User.objects.create_user(username=username, email=email or f"{username}@member.test", password="whatever-123")
    User.objects.filter(pk=user.pk).update(is_verified_email=True)
    EntityUser.objects.get_or_create(user=user, entity=tenant["entity"])
    return user


def _plain(user):
    """The stored plaintext, read WITHOUT going through reveal() (which audits)."""
    return decrypt_text(UserTemporaryPassword.objects.get(user=user).encrypted, purpose=service.PURPOSE)


def _issue(user, tenant=None):
    service.issue(user, entity_id=tenant["entity"].id if tenant else None)
    return _plain(user)


def _client(tenant):
    tenant["client"].raise_request_exception = False
    return tenant["client"]


def _url(user, action):
    return f"/api/django_resaas/users/{user.id}/{action}/"


def _login(identifier, password):
    return APIClient(raise_request_exception=False).post(
        "/api/login/", {"identifier": identifier, "password": password}, format="json"
    )


def _change(identifier, password, new_password):
    return APIClient(raise_request_exception=False).post(
        "/api/password/change/temporary/",
        {"identifier": identifier, "password": password, "new_password": new_password},
        format="json",
    )


# ---------------------------------------------------------------- generation

class TestGeneration:

    def test_passwords_are_long_random_and_use_every_character_class(self):
        passwords = {service.generate() for _ in range(50)}

        assert len(passwords) == 50
        for password in passwords:
            assert len(password) == service.LENGTH
            assert any(c.isupper() for c in password)
            assert any(c.islower() for c in password)
            assert any(c.isdigit() for c in password)
            assert any(not c.isalnum() for c in password)

    def test_a_new_person_gets_a_user_with_a_temporary_password(self):
        person = Person.objects.create(name="Joao", surname="Manuel")
        user = person.user

        assert user.has_usable_password()
        assert user.must_change_password
        assert service.state_of(user) == service.TEMPORARY
        assert AuditLog.objects.filter(action=service.CREATED, object_id=str(user.pk)).exists()

    def test_expiry_is_configurable_and_defaults_to_72_hours(self, settings):
        assert service.ttl_hours() == 72
        settings.TEMPORARY_PASSWORD_TTL_HOURS = 24
        assert service.ttl_hours() == 24


# ---------------------------------------------------------------- storage

class TestStoredEncrypted:

    def test_the_copy_is_ciphertext_and_the_password_is_hashed_as_usual(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-store"))
        password = _issue(user)

        row = UserTemporaryPassword.objects.get(user=user)

        assert row.encrypted and password not in row.encrypted
        assert decrypt_text(row.encrypted, purpose=service.PURPOSE) == password
        user.refresh_from_db()
        assert user.password.startswith(("pbkdf2_", "argon2", "bcrypt", "scrypt"))
        assert user.check_password(password)

    def test_the_plaintext_appears_nowhere_in_the_database(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-db")
        user = _member(tenant)
        password = _issue(user, tenant)
        _client(tenant).post(_url(user, "viewTemporaryPassword"))  # writes an audit row too

        with connection.cursor() as cursor:
            for table in ("django_resaas_usertemporarypassword", "django_resaas_user", "django_resaas_auditlog"):
                cursor.execute(f"SELECT * FROM {table}")
                dump = " ".join(str(value) for row in cursor.fetchall() for value in row)
                assert password not in dump, table

    def test_the_normal_user_serializer_and_endpoint_never_expose_it(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-serializer")
        user = _member(tenant)
        password = _issue(user, tenant)

        data = UserSerializer(user).data
        response = _client(tenant).get(f"/api/django_resaas/users/{user.id}/")

        for payload in (data, response.data):
            text = str(dict(payload))
            assert password not in text
            assert "temporary" not in text.lower() and "encrypted" not in text.lower() and "password" not in text.lower()

    def test_secret_box_round_trips_and_rejects_tampering(self):
        token = encrypt_text("R7@mK9#pQ2xL", purpose="x")

        assert decrypt_text(token, purpose="x") == "R7@mK9#pQ2xL"
        with pytest.raises(SecretBoxError):
            decrypt_text(token, purpose="another-purpose")
        with pytest.raises(SecretBoxError):
            decrypt_text(token[:-4] + "AAAA", purpose="x")


# ---------------------------------------------------------------- viewing

class TestView:

    def test_an_authorised_administrator_can_view_it(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-view")
        user = _member(tenant)
        password = _issue(user, tenant)

        response = _client(tenant).post(_url(user, "viewTemporaryPassword"))

        assert response.status_code == 200
        assert response.data["password"] == password
        assert response["Cache-Control"] == "no-store"
        assert response.data["state"] == "temporary" and response.data["expires_at"]

    def test_without_the_permission_it_is_refused_and_nothing_is_audited(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-denied")
        user = _member(tenant)
        _issue(user, tenant)

        with mock.patch(PERMISSION_CHECK, return_value=False):
            response = _client(tenant).post(_url(user, "viewTemporaryPassword"))

        assert response.status_code == 403 and response.data["code"] == "permission_denied"
        assert "password" not in response.data
        assert not AuditLog.objects.filter(action=service.VIEWED).exists()

    def test_view_user_alone_is_not_enough(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-view-user")
        user = _member(tenant)
        _issue(user, tenant)

        only_view_user = lambda request, role: role == "view_user"  # noqa: E731
        with mock.patch(PERMISSION_CHECK, side_effect=only_view_user):
            details = _client(tenant).get(_url(user, "passwordSecurity"))
            revealed = _client(tenant).post(_url(user, "viewTemporaryPassword"))

        assert details.status_code == 200 and "password" not in details.data
        assert revealed.status_code == 403

    def test_anonymous_requests_are_refused(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-anon"))
        _issue(user)

        anonymous = APIClient(raise_request_exception=False)

        assert anonymous.post(_url(user, "viewTemporaryPassword")).status_code in (401, 403)
        assert anonymous.post(_url(user, "regenerateTemporaryPassword")).status_code in (401, 403)

    def test_another_entitys_user_cannot_be_viewed(self, bootstrap_tenant):
        mine = bootstrap_tenant("tp-cross-a")
        theirs = bootstrap_tenant("tp-cross-b")
        victim = _member(theirs, "victim")
        password = _issue(victim, theirs)

        response = _client(mine).post(_url(victim, "viewTemporaryPassword"))

        assert response.status_code == 404 and response.data["code"] == "user_not_found"
        assert password not in str(response.data)
        assert not AuditLog.objects.filter(action=service.VIEWED).exists()

    def test_a_user_with_no_membership_is_manageable_where_it_was_issued(self, bootstrap_tenant):
        """An account provisioned from a Person belongs to no entity yet: the
        entity whose context issued the password can manage it - no other."""
        mine = bootstrap_tenant("tp-scope-a")
        theirs = bootstrap_tenant("tp-scope-b")
        user = User.objects.create_user(username="provisioned", email=None, password="x")
        _issue(user, mine)

        assert _client(mine).post(_url(user, "viewTemporaryPassword")).status_code == 200
        assert _client(theirs).post(_url(user, "viewTemporaryPassword")).status_code == 404

    def test_viewing_is_audited_without_the_password(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-audit")
        user = _member(tenant)
        password = _issue(user, tenant)

        _client(tenant).post(_url(user, "viewTemporaryPassword"), REMOTE_ADDR="10.1.2.3")

        event = AuditLog.objects.get(action=service.VIEWED)
        assert event.user_id == tenant["user"].id
        assert event.object_id == str(user.pk) and event.model == "User"
        assert event.entity_id == tenant["entity"].id
        assert event.ip_address == "10.1.2.3"
        assert password not in " ".join(str(getattr(event, f.name)) for f in event._meta.fields)

    def test_the_plaintext_never_reaches_the_logs(self, bootstrap_tenant, caplog):
        tenant = bootstrap_tenant("tp-logs")
        user = _member(tenant)

        with caplog.at_level(logging.DEBUG):
            password = _issue(user, tenant)
            _client(tenant).post(_url(user, "viewTemporaryPassword"))
            _client(tenant).post(_url(user, "regenerateTemporaryPassword"))
            _login(user.username, password)

        assert password not in caplog.text

    def test_a_permanent_password_is_never_revealed(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-permanent")
        user = _member(tenant)
        password = _issue(user, tenant)
        _change(user.username, password, "My-own-Password-1")

        response = _client(tenant).post(_url(user, "viewTemporaryPassword"))

        assert response.status_code == 404 and response.data["code"] == "no_temporary_password"
        assert not UserTemporaryPassword.objects.filter(user=user).exists()


# ---------------------------------------------------------------- expiry

class TestExpiry:

    def _expire(self, user):
        UserTemporaryPassword.objects.filter(user=user).update(expires_at=timezone.now() - timedelta(minutes=1))

    def test_an_expired_password_is_not_revealed_again(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-expired")
        user = _member(tenant)
        password = _issue(user, tenant)
        self._expire(user)

        response = _client(tenant).post(_url(user, "viewTemporaryPassword"))

        assert response.status_code == 410 and response.data["code"] == "temporary_password_expired"
        assert password not in str(response.data)
        # the recoverable copy is gone, and the expiry audited once
        assert UserTemporaryPassword.objects.get(user=user).encrypted is None
        _client(tenant).post(_url(user, "viewTemporaryPassword"))
        assert AuditLog.objects.filter(action=service.EXPIRED_EVENT, object_id=str(user.pk)).count() == 1

    def test_the_details_report_expired_and_offer_no_view(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-expired-details")
        user = _member(tenant)
        _issue(user, tenant)
        self._expire(user)

        details = _client(tenant).get(_url(user, "passwordSecurity")).data

        assert details["state"] == "expired" and details["can_reveal"] is False

    def test_the_details_carry_a_read_only_two_factor_summary(self, bootstrap_tenant):
        from django_resaas.saas.core.services import two_factor_service

        tenant = bootstrap_tenant("tp-two-factor-summary")
        user = _member(tenant)
        _issue(user, tenant)

        before = _client(tenant).get(_url(user, "passwordSecurity")).data["two_factor"]
        two_factor_service.begin_setup(user)
        after_pending = _client(tenant).get(_url(user, "passwordSecurity")).data["two_factor"]

        assert before["state"] == "not_configured" and before["policy"] in ("optional", "required", "disabled")
        assert after_pending["state"] == "not_configured"     # a half-finished setup is not active
        assert set(before) == {"policy", "state"}             # never a secret or a code

    def test_an_expired_password_cannot_log_in(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-expired-login"))
        password = _issue(user)
        self._expire(user)

        assert _login(user.username, password).status_code in (401, 403)
        assert _change(user.username, password, "My-own-Password-1").status_code == 401

    def test_only_a_new_password_can_follow_an_expiry(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-expired-regen")
        user = _member(tenant)
        _issue(user, tenant)
        self._expire(user)

        assert _client(tenant).post(_url(user, "regenerateTemporaryPassword")).status_code == 200
        assert _client(tenant).post(_url(user, "viewTemporaryPassword")).status_code == 200

    def test_the_sweep_retires_every_overdue_copy(self, bootstrap_tenant):
        first, second = _member(bootstrap_tenant("tp-sweep"), "one"), User.objects.create_user(username="two", email="two@x.com", password="x")
        _issue(first)
        _issue(second)
        self._expire(first)

        assert service.expire_overdue() == 1
        assert UserTemporaryPassword.objects.get(user=first).encrypted is None
        assert UserTemporaryPassword.objects.get(user=second).encrypted


# ---------------------------------------------------------------- regeneration

class TestRegenerate:

    def test_the_previous_password_is_gone_and_the_new_one_is_viewable(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-regen")
        user = _member(tenant)
        old = _issue(user, tenant)
        old_ciphertext = UserTemporaryPassword.objects.get(user=user).encrypted

        response = _client(tenant).post(_url(user, "regenerateTemporaryPassword"))
        assert response.status_code == 200 and "password" not in response.data

        assert UserTemporaryPassword.objects.filter(user=user).count() == 1
        assert UserTemporaryPassword.objects.get(user=user).encrypted != old_ciphertext
        new = _client(tenant).post(_url(user, "viewTemporaryPassword")).data["password"]
        assert new != old
        assert not User.objects.get(pk=user.pk).check_password(old)
        assert User.objects.get(pk=user.pk).check_password(new)
        assert AuditLog.objects.filter(action=service.REGENERATED, object_id=str(user.pk), user=tenant["user"]).exists()

    def test_it_needs_its_own_permission(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-regen-denied")
        user = _member(tenant)
        _issue(user, tenant)

        only_view = lambda request, role: role == "view_temporary_password"  # noqa: E731
        with mock.patch(PERMISSION_CHECK, side_effect=only_view):
            response = _client(tenant).post(_url(user, "regenerateTemporaryPassword"))

        assert response.status_code == 403

    def test_another_entitys_user_cannot_be_regenerated(self, bootstrap_tenant):
        mine = bootstrap_tenant("tp-regen-a")
        theirs = bootstrap_tenant("tp-regen-b")
        victim = _member(theirs, "victim")
        password = _issue(victim, theirs)

        assert _client(mine).post(_url(victim, "regenerateTemporaryPassword")).status_code == 404
        assert User.objects.get(pk=victim.pk).check_password(password)

    def test_you_cannot_regenerate_your_own_password(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-regen-self")

        response = _client(tenant).post(_url(tenant["user"], "regenerateTemporaryPassword"))

        assert response.status_code == 400 and response.data["code"] == "cannot_regenerate_own_password"

    def test_a_definitive_password_can_be_replaced_by_a_new_temporary_one(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-regen-permanent")
        user = _member(tenant)

        assert service.state_of(user) == service.PERMANENT
        assert _client(tenant).post(_url(user, "regenerateTemporaryPassword")).status_code == 200
        assert service.state_of(user) == service.TEMPORARY


# ---------------------------------------------------------------- first login

class TestFirstLogin:

    def test_the_first_login_gives_no_session_and_demands_a_new_password(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-login"))
        password = _issue(user)

        response = _login(user.username, password)

        assert response.status_code == 200
        assert response.data["must_change_password"] is True
        assert response.data["tokens"] is None
        assert User.objects.get(pk=user.pk).last_login is None

    def test_an_account_without_e_mail_can_log_in_with_its_temporary_password(self):
        person = Person.objects.create(name="Semmail", surname="Silva")
        password = _plain(person.user)

        response = _login(person.user.username, password)

        assert response.status_code == 200 and response.data["must_change_password"] is True

    def test_changing_it_removes_the_copy_audits_and_opens_the_session(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-change"))
        password = _issue(user)

        response = _change(user.username, password, "My-own-Password-1")

        assert response.status_code == 200
        assert response.data["tokens"]["access"] and response.data["must_change_password"] is False
        assert not UserTemporaryPassword.objects.filter(user=user).exists()
        assert not User.objects.get(pk=user.pk).must_change_password
        assert User.objects.get(pk=user.pk).check_password("My-own-Password-1")
        assert not User.objects.get(pk=user.pk).check_password(password)
        assert AuditLog.objects.filter(action=service.CHANGED, object_id=str(user.pk)).exists()

    def test_any_other_password_change_route_also_destroys_the_copy(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-other-route"))
        _issue(user)

        user.set_password("Set-by-reset-flow-1")
        user.save()

        assert not UserTemporaryPassword.objects.filter(user=user).exists()
        assert AuditLog.objects.filter(action=service.CHANGED, object_id=str(user.pk)).exists()

    def test_the_change_rejects_weak_wrong_or_repeated_passwords(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-change-bad"))
        password = _issue(user)

        assert _change(user.username, password, "short").status_code == 400
        assert _change(user.username, password, password).status_code == 400
        assert _change(user.username, "wrong-password", "My-own-Password-1").status_code == 401
        assert _change("nobody", password, "My-own-Password-1").status_code == 401
        assert UserTemporaryPassword.objects.filter(user=user).exists()

    def test_a_definitive_password_cannot_use_the_first_login_endpoint(self, bootstrap_tenant):
        user = _member(bootstrap_tenant("tp-change-permanent"))
        user.set_password("Already-definitive-1")
        user.save()

        assert _change(user.username, "Already-definitive-1", "Another-Password-1").status_code == 401

    def test_after_the_change_the_view_action_is_gone(self, bootstrap_tenant):
        tenant = bootstrap_tenant("tp-gone")
        user = _member(tenant)
        password = _issue(user, tenant)
        _change(user.username, password, "My-own-Password-1")

        details = _client(tenant).get(_url(user, "passwordSecurity")).data

        assert details["state"] == "permanent"
        assert details["can_reveal"] is False and details["must_change_password"] is False
        assert details["expires_at"] is None
        assert _login(user.username, "My-own-Password-1").data["tokens"]["access"]

    def test_an_ordinary_login_is_unchanged(self, bootstrap_tenant):
        user = User.objects.create_user(username="ordinary", email="ordinary@member.test", password="Ordinary-Pass-1")
        User.objects.filter(pk=user.pk).update(is_verified_email=True)

        response = _login("ordinary", "Ordinary-Pass-1")

        assert response.status_code == 200 and response.data["tokens"]["access"]
        assert response.data["must_change_password"] is False


# ---------------------------------------------------------------- permissions

def test_the_sensitive_permissions_exist_and_root_holds_them(bootstrap_tenant):
    from django.contrib.auth.models import Permission

    tenant = bootstrap_tenant("tp-perms")
    codenames = {"view_temporary_password", "regenerate_temporary_password"}

    assert set(Permission.objects.filter(codename__in=codenames).values_list("codename", flat=True)) == codenames
    assert codenames <= set(tenant["root_group"].permissions.values_list("codename", flat=True))


def test_the_actions_are_protected_resaas_actions_declaring_their_permission():
    from django_resaas.saas.data.user.views.user import UserAPIView

    declared = {
        name: getattr(UserAPIView, name)._resaas_action["permission"]
        for name in ("passwordSecurity", "viewTemporaryPassword", "regenerateTemporaryPassword")
    }

    assert declared == {
        "passwordSecurity": "view_user",
        "viewTemporaryPassword": "view_temporary_password",
        "regenerateTemporaryPassword": "regenerate_temporary_password",
    }


def test_the_expiry_command_retires_overdue_copies(bootstrap_tenant):
    from io import StringIO
    from django.core.management import call_command

    user = _member(bootstrap_tenant("tp-command"))
    _issue(user)
    UserTemporaryPassword.objects.filter(user=user).update(expires_at=timezone.now() - timedelta(hours=1))

    out = StringIO()
    call_command("expire_temporary_passwords", stdout=out)

    assert "1 temporary password(s) expired." in out.getvalue()
    assert UserTemporaryPassword.objects.get(user=user).encrypted is None

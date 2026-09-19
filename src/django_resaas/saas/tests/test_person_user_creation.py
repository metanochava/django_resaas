"""CREATE Person -> creates its User (username from the FIRST NAME only,
UNIQUE in the database); UPDATE Person -> never creates a User and never
touches a username. See core/services/person_user_service.py."""
import re

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from django_resaas.saas.core.services import person_user_service as service
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db

User = get_user_model()

SUFFIXED = re.compile(r"^joao\.[0-9a-f]{6}$")


def _person(name, surname="Silva", **extra):
    return Person.objects.create(name=name, surname=surname, **extra)


# =============================================================
# USERNAME FROM THE FIRST NAME ONLY
# =============================================================

@pytest.mark.parametrize("name, surname, expected", [
    ("João", "Silva", "joao"),
    ("João Manuel", "Silva", "joao"),
    ("Álvaro", "Cossa", "alvaro"),
    ("José", "dos Santos", "jose"),
    ("Érica", "Mabjaia", "erica"),
    ("Maria José", "Cossa", "maria"),
    ("Ana Paula", "Chavana", "ana"),
])
def test_username_is_the_normalised_first_name_only(name, surname, expected):
    person = _person(name, surname)

    assert person.user.username == expected


def test_the_surname_is_never_used_even_when_the_name_is_taken():
    _person("João", "Silva")
    second = _person("João", "Cossa")

    assert SUFFIXED.match(second.user.username)
    assert "cossa" not in second.user.username
    assert "silva" not in second.user.username


def test_repeated_first_names_get_joao_then_random_suffixes():
    usernames = [_person("João", surname).user.username for surname in ("A", "B", "C")]

    assert usernames[0] == "joao"
    assert SUFFIXED.match(usernames[1]) and SUFFIXED.match(usernames[2])
    assert len(set(usernames)) == 3


def test_a_taken_username_is_detected_regardless_of_case():
    User.objects.create_user(username="Joao", email="orphan@example.com")

    assert SUFFIXED.match(_person("João").user.username)


@pytest.mark.parametrize("raw, expected", [
    ("João", "joao"),
    ("ÁLVARO", "alvaro"),
    ("Ana-Maria", "anamaria"),
    ("O'Brien", "obrien"),
    ("  Zé  ", "ze"),
    ("Jo@o!#", "joo"),
])
def test_normalisation_lowercases_strips_accents_and_invalid_characters(raw, expected):
    assert service.normalize_username_base(raw) == expected


@pytest.mark.parametrize("name", [None, "", "   ", "!!!", "@#$", "日本語"])
def test_no_usable_first_name_gives_a_neutral_username_never_an_empty_one(name):
    username = service.generate_unique_username(name)

    assert re.match(r"^user\.[0-9a-f]{6}$", username)


def test_a_person_without_a_usable_first_name_still_gets_a_user():
    person = _person("", "Silva")

    assert re.match(r"^user\.[0-9a-f]{6}$", person.user.username)
    assert "silva" not in person.user.username


def test_username_never_exceeds_the_field_max_length(monkeypatch):
    field = User._meta.get_field("username")
    monkeypatch.setattr(field, "max_length", 10)

    long_first = service.generate_unique_username("Aleksandrovich")
    assert len(long_first) <= 10

    _person("Aleksandrovich")
    taken = service.generate_unique_username("Aleksandrovich")
    assert len(taken) <= 10
    assert re.match(r"^[a-z0-9]+\.[0-9a-f]{6}$", taken)


# =============================================================
# UNIQUE IN THE DATABASE
# =============================================================

def test_username_is_really_unique_in_the_database():
    assert User._meta.get_field("username").unique is True

    User.objects.create_user(username="dup", email="a@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username="dup", email="b@example.com")


# =============================================================
# CREATE vs UPDATE
# =============================================================

def test_creating_a_person_creates_exactly_one_linked_user():
    before = User.objects.count()

    person = _person("Helena", "Marrengula", email="helena@example.com")

    assert User.objects.count() == before + 1
    person.refresh_from_db()
    assert person.user.username == "helena"
    assert person.user.email == "helena@example.com"
    assert (person.user.first_name, person.user.last_name) == ("Helena", "Marrengula")
    assert person.user.has_usable_password() is False
    assert Person.objects.filter(user=person.user).count() == 1


def test_updating_a_person_creates_no_user_and_keeps_the_username():
    person = _person("João", "Silva")
    users = User.objects.count()

    person.name = "Carlos"
    person.surname = "Manuel"
    person.save()

    assert User.objects.count() == users
    person.refresh_from_db()
    assert person.user.username == "joao"


def test_an_old_person_without_a_user_stays_without_one_after_update():
    person = _person("Rui", "Cossa")
    Person.objects.filter(pk=person.pk).update(user=None)
    User.objects.filter(username="rui").delete()
    users = User.objects.count()

    person.refresh_from_db()
    person.surname = "Chavana"
    person.save()

    person.refresh_from_db()
    assert person.user is None
    assert User.objects.count() == users


def test_saving_again_never_creates_additional_users():
    person = _person("Nelson")
    users = User.objects.count()

    for _ in range(3):
        person.save()

    assert User.objects.count() == users


def test_a_person_created_by_the_user_signal_does_not_get_a_second_user():
    """User -> Person (existing) must not loop back into Person -> User."""
    users, persons = User.objects.count(), Person.objects.count()

    user = User.objects.create_user(username="fromuser", email="fromuser@example.com")

    assert User.objects.count() == users + 1
    assert Person.objects.count() == persons + 1
    assert Person.objects.get(user=user)


def test_a_person_created_with_a_user_already_linked_gets_no_extra_user():
    user = User.objects.create_user(username="linked", email="linked@example.com")
    Person.objects.filter(user=user).delete()
    users = User.objects.count()

    Person.objects.create(name="Linked", user=user)

    assert User.objects.count() == users


# =============================================================
# CONCURRENCY
# =============================================================

def test_a_username_collision_lost_to_another_worker_is_retried_with_a_suffix(monkeypatch):
    """Two workers both saw 'joao' free; one wins the UNIQUE constraint, the
    other must recover with joao.<suffix> instead of failing."""
    winner = User.objects.create_user(username="joao", email="winner@example.com")
    Person.objects.filter(user=winner).delete()

    real = service.generate_unique_username
    calls = []

    def racing(name, *, force_suffix=False):
        calls.append(force_suffix)
        return "joao" if len(calls) == 1 else real(name, force_suffix=force_suffix)

    monkeypatch.setattr(service, "generate_unique_username", racing)

    person = _person("João", "Loser")

    assert calls == [False, True]
    assert SUFFIXED.match(person.user.username)
    assert User.objects.filter(username="joao").count() == 1


def test_an_integrity_error_that_is_not_a_username_collision_is_not_hidden():
    taken = User.objects.create_user(username="someone", email="taken@example.com")
    Person.objects.filter(user=taken).delete()

    with pytest.raises(IntegrityError):
        _person("Ana", "Costa", email="taken@example.com")


def test_gives_up_after_a_bounded_number_of_collisions(monkeypatch):
    User.objects.create_user(username="stuck", email="stuck@example.com")

    monkeypatch.setattr(service, "generate_unique_username", lambda name, *, force_suffix=False: "stuck")

    with pytest.raises(IntegrityError):
        service.create_user_for_person(Person(name="Stuck"))


# ---- Person payload exposes the linked account summary (profile view) ----

@pytest.mark.django_db
def test_person_payload_exposes_only_the_user_account_summary():
    from django_resaas.saas.data.person.serializers.person import PersonSerializer

    person = _person("Ana", "Costa")
    person.user.email = "ana@example.com"
    person.user.mobile = "841110000"
    person.user.is_verified_email = True
    person.user.save(update_fields=["email", "mobile", "is_verified_email"])

    data = PersonSerializer(Person.objects.get(pk=person.pk), context={}).data["user_data"]

    assert set(data) == {"id", "username", "email", "mobile", "is_verified_mobile", "is_verified_email", "profile"}
    assert data["username"] == person.user.username
    assert data["email"] == "ana@example.com"
    assert data["is_verified_email"] is True
    assert data["is_verified_mobile"] is False
    assert "theme" not in data and "password" not in data


@pytest.mark.django_db
def test_person_payload_user_data_is_null_without_a_user():
    from django_resaas.saas.data.person.serializers.person import PersonSerializer

    person = _person("Ana", "Costa")
    Person.objects.filter(pk=person.pk).update(user=None)

    assert PersonSerializer(Person.objects.get(pk=person.pk), context={}).data["user_data"] is None

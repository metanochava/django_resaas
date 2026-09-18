"""
Centralised Person duplicate-detection.

Any flow that is about to create a new Person (add_employee today;
future Patient/Student/Customer intake flows) should search for
candidates through here FIRST instead of re-implementing its own
ad-hoc matching - keeps the matching rules (and their future tuning)
in one place, reusable, and out of any single business module's view/
component (see CLAUDE.md's "Person Matching -> Employee -> Patient ->
Student -> Customer" reuse note).

Deliberately read-only and side-effect free: callers decide what to do
with the candidates (this module never creates/merges/blocks anything
itself).
"""
import re

from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q, Value
from django.db.models.functions import Replace

from django_resaas.saas.models.person import Person
from django_resaas.saas.models.document import Document


def normalize_email(value):
    value = (value or "").strip().lower()
    return value or None


def normalize_phone_digits(value):
    digits = re.sub(r"\D", "", value or "")
    return digits or None


def normalize_document_number(value):
    return re.sub(r"[^A-Za-z0-9]", "", (value or "")).upper()


def normalize_name(value):
    value = re.sub(r"\s+", " ", (value or "").strip())
    return value.casefold() or None


# Trailing digits compared for a phone match - tolerant of formatting
# differences (spaces, dashes, a leading country code) between what the
# user typed and however the existing Person's number was originally
# stored, without needing to renormalize/migrate existing data. Long
# enough that two unrelated real phone numbers colliding is very
# unlikely for the number lengths RESAAS actually deals with.
PHONE_TAIL_LENGTH = 8

# Document matching is scoped by `tipo` first (usually a small result
# set per type), then compared in Python with normalize_document_number()
# so formatting differences (spaces, dashes) in an existing record don't
# cause a real match to be missed - a DB-level `numero__iexact` alone
# would miss "123 456 789" vs "123456789".
def _match_documents(person_ct, documents):
    matched_person_ids = set()

    for doc in documents or []:
        tipo = doc.get("tipo")
        numero = normalize_document_number(doc.get("numero"))

        if not tipo or not numero:
            continue

        rows = Document.objects.filter(
            content_type=person_ct,
            tipo_id=tipo,
        ).values_list("object_id", "numero")

        for object_id, stored_numero in rows:
            if normalize_document_number(stored_numero) == numero:
                matched_person_ids.add(str(object_id))

    return matched_person_ids


def _match_email(email):
    email = normalize_email(email)
    if not email:
        return set()

    return set(
        str(pid) for pid in
        Person.objects.filter(email=email).values_list("id", flat=True)
    )


def _digits_only_expr(field_name):
    # A stored phone keeps whatever punctuation the person who entered
    # it used ("+258 84 123 4567", "258-84-123-4567", ...) - comparing
    # a digits-only tail against the RAW stored value with __contains
    # would miss it the moment any of those separators falls inside the
    # matched window. Stripping the same separators at the DB level
    # (via chained Replace()) keeps the comparison scalable (still a
    # single indexed-ish query) instead of pulling every row into
    # Python to renormalize.
    expr = F(field_name)
    for separator in (" ", "-", "(", ")", "+"):
        expr = Replace(expr, Value(separator), Value(""))
    return expr


def _match_phone(phone, alternative_phone):
    tails = {
        digits[-PHONE_TAIL_LENGTH:]
        for digits in (
            normalize_phone_digits(phone),
            normalize_phone_digits(alternative_phone),
        )
        if digits and len(digits) >= PHONE_TAIL_LENGTH
    }

    if not tails:
        return set()

    candidates = Person.objects.annotate(
        _phone_digits=_digits_only_expr("phone"),
        _alt_phone_digits=_digits_only_expr("alternative_phone"),
    )

    q = Q()
    for tail in tails:
        q |= Q(_phone_digits__endswith=tail) | Q(_alt_phone_digits__endswith=tail)

    return set(
        str(pid) for pid in
        candidates.filter(q).values_list("id", flat=True)
    )


def _match_name_and_birth_date(name, middle_name, surname, date_of_birth):
    name = normalize_name(name)
    surname = normalize_name(surname)

    # A name alone (or even name+surname without a birth date) is too
    # weak a signal on its own - CLAUDE.md's own instruction not to
    # assume two people are the same just because the names look
    # similar. Only counted once corroborated by a real date of birth.
    if not (name and surname and date_of_birth):
        return set()

    return set(
        str(pid) for pid in
        Person.objects.filter(
            name__iexact=name,
            surname__iexact=surname,
            date_of_birth=date_of_birth,
        ).values_list("id", flat=True)
    )


def find_candidates(data, limit=10):
    """
    data: {
        "email": str, "phone": str, "alternative_phone": str,
        "name": str, "middle_name": str, "surname": str,
        "date_of_birth": "YYYY-MM-DD",
        "documents": [{"tipo": <DocumentType id>, "numero": str}, ...]
    }

    Returns a list of {"person": Person, "matched_fields": [str, ...]}
    ordered by strength of match (document > email > phone > name+dob),
    most-matched-fields first within the same strongest signal.
    """
    data = data or {}
    person_ct = ContentType.objects.get_for_model(Person)

    signals = [
        ("document", _match_documents(person_ct, data.get("documents"))),
        ("email", _match_email(data.get("email"))),
        ("phone", _match_phone(data.get("phone"), data.get("alternative_phone"))),
        (
            "name_and_birth_date",
            _match_name_and_birth_date(
                data.get("name"), data.get("middle_name"),
                data.get("surname"), data.get("date_of_birth"),
            ),
        ),
    ]

    matched_fields_by_person = {}

    for label, person_ids in signals:
        for pid in person_ids:
            matched_fields_by_person.setdefault(pid, []).append(label)

    if not matched_fields_by_person:
        return []

    signal_rank = {label: i for i, (label, _) in enumerate(signals)}

    def strongest_rank(pid):
        return min(signal_rank[f] for f in matched_fields_by_person[pid])

    ordered_ids = sorted(
        matched_fields_by_person,
        key=lambda pid: (strongest_rank(pid), -len(matched_fields_by_person[pid])),
    )[:limit]

    persons_by_id = {
        str(p.id): p
        for p in Person.objects.filter(id__in=ordered_ids)
    }

    return [
        {
            "person": persons_by_id[pid],
            "matched_fields": matched_fields_by_person[pid],
        }
        for pid in ordered_ids
        if pid in persons_by_id
    ]

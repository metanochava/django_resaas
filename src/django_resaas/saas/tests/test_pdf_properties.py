"""PDF() fills the document properties of every PDF: Producer is
"<EntityType> - <Entity>" of the request's tenant, Author the user logged in
when it is produced, Title/Subject/Keywords from pdf_subject + pdf_person, and
the file is named <Subject>_<Person>_<date>.pdf."""
import re
import zlib

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from django_resaas.saas.core.utils import PDF
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db

HTML = "<html><head><title>Old title</title></head><body><p>Hello</p></body></html>"


def _info(pdf_bytes, key):
    """A value of the PDF info dictionary: /Key (value), looked up in the file
    and in every Flate stream (WeasyPrint packs objects into object streams)."""
    chunks = [pdf_bytes]
    for stream in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.S):
        try:
            chunks.append(zlib.decompress(stream.group(1)))
        except zlib.error:
            pass
    for chunk in chunks:
        match = re.search(rb"/" + key.encode() + rb" ?\((.*?)(?<!\\)\)", chunk, re.S)
        if match:
            value = match.group(1)
            if value.startswith(b"\xfe\xff"):
                return value[2:].decode("utf-16-be")
            return value.decode("latin-1")
    return None


def _request(tenant, user=None):
    request = APIRequestFactory().get("/")
    request.entity_id = tenant["entity"].id
    request.user = user or tenant["user"]
    return request


def test_properties_and_file_name(bootstrap_tenant):
    tenant = bootstrap_tenant("pdf-properties")
    user = tenant["user"]
    person = Person.objects.filter(user=user).first() or Person(user=user, gender="F")
    person.name, person.surname = "Ana", "Mabote"
    person.save()
    user.refresh_from_db()
    entity = tenant["entity"]
    entity_type = entity.entity_type
    type_name = entity_type.label or entity_type.name

    response = PDF(HTML, _request(tenant, user), pdf_subject="Medical Certificate", pdf_person="Elsa Nhaca")

    pdf = response.content
    assert pdf.startswith(b"%PDF")
    assert _info(pdf, "Producer") == f"{type_name} - {entity.name}"
    assert _info(pdf, "Author") == "Ana Mabote"
    assert _info(pdf, "Creator") == "RESAAS"
    assert _info(pdf, "Title") == "Medical Certificate - Elsa Nhaca"
    assert _info(pdf, "Subject") == "Medical Certificate"
    assert "Elsa Nhaca" in _info(pdf, "Keywords")
    assert _info(pdf, "CreationDate")
    today = timezone.localdate().isoformat()
    assert response["Content-Disposition"] == (
        f'inline; filename="MedicalCertificate-ElsaNhaca_{today}.pdf"; '
        f"filename*=UTF-8''MedicalCertificate-ElsaNhaca_{today}.pdf"
    )


def test_explicit_name_and_title_are_kept_and_accents_are_safe(bootstrap_tenant):
    tenant = bootstrap_tenant("pdf-properties-named")

    response = PDF(HTML, _request(tenant), doc={"name": "QR Clínica São José"}, download=True)

    today = timezone.localdate().isoformat()
    assert response["Content-Disposition"] == (
        f'attachment; filename="QRClinicaSaoJose_{today}.pdf"; '
        f"filename*=UTF-8''QRCl%C3%ADnicaS%C3%A3oJos%C3%A9_{today}.pdf"
    )
    assert _info(response.content, "Title") == "Old title"


def test_without_tenant_or_user_it_still_renders(bootstrap_tenant):
    request = APIRequestFactory().get("/")

    response = PDF(HTML, request)

    assert response.content.startswith(b"%PDF")
    assert "WeasyPrint" in (_info(response.content, "Producer") or "")
    today = timezone.localdate().isoformat()
    assert response["Content-Disposition"] == f"inline; filename=\"Oldtitle_{today}.pdf\"; filename*=UTF-8''Oldtitle_{today}.pdf"

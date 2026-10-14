"""The schema's endpoints follow the view actually registered for the model
(ResaasSchemaBuilder.endpoint_base): a view registered under its own name
(@register_view("journalentries")) must not get a schema pointing at the
default "<model>s" URL, which answers 404."""
import pytest
from rest_framework import serializers, viewsets

from django_resaas.saas.core.base.registry import VIEW_REGISTRY
from django_resaas.saas.core.schema.builder import ResaasSchemaBuilder
from django_resaas.saas.models.language import Language

pytestmark = pytest.mark.django_db


class _LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "name"]


class _NamedLanguageView(viewsets.ModelViewSet):
    queryset = Language.objects.all()
    serializer_class = _LanguageSerializer


@pytest.fixture
def registered(monkeypatch):
    views = dict(VIEW_REGISTRY.get("django_resaas", {}))
    views = {name: cls for name, cls in views.items()
             if getattr(getattr(cls, "queryset", None), "model", None) is not Language}
    views["idiomas"] = _NamedLanguageView
    monkeypatch.setitem(VIEW_REGISTRY, "django_resaas", views)


def test_a_named_view_gives_its_own_endpoint(registered):
    builder = ResaasSchemaBuilder(Language)

    assert builder.endpoint_base() == "django_resaas/idiomas"
    assert builder.build_pdf()["detail_endpoint"] == "django_resaas/idiomas/{id}/pdf/"
    assert builder.build_pdf()["list_endpoint"] == "django_resaas/idiomas/pdf_list/"


def test_without_a_registered_view_the_default_is_kept(monkeypatch):
    views = {name: cls for name, cls in VIEW_REGISTRY.get("django_resaas", {}).items()
             if getattr(getattr(cls, "queryset", None), "model", None) is not Language}
    monkeypatch.setitem(VIEW_REGISTRY, "django_resaas", views)

    assert ResaasSchemaBuilder(Language).endpoint_base() == "django_resaas/languages"


def test_an_explicit_resaas_endpoint_wins(registered, monkeypatch):
    builder = ResaasSchemaBuilder(Language)
    monkeypatch.setattr(builder, "get_resaas_value",
                        lambda name, default=None: "custom/langs/" if name == "endpoint" else default)

    assert builder.endpoint_base() == "custom/langs"

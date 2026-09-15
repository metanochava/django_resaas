"""Reported live: `list_user` view "tem problemas" - traced to
`User.RESAAS.routes['list']` being copy-pasted from `add_user` instead
of `list_user` (visible in the scaffold/IDE's SchemaInspector.vue,
which renders the schema's raw `routes` dict). ResaasSchemaBuilder's
own default (no explicit `routes` override) is the correct
`f"list_{model}"` convention (see build_routes() in
core/schema/builder.py) - the same copy-paste mistake was found on 14
other models (all overriding `routes['list']` to their own `add_*`
value instead of `list_*`), all fixed the same way."""
import pytest

from django_resaas.saas.core.schema.builder import ResaasSchemaBuilder
from django_resaas.saas.models.user import User
from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.address import Address
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.animation_setting import AnimationSetting
from django_resaas.saas.models.app import App
from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.models.theme_surface import ThemeSurface
from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.person import Person
from django_resaas.saas.models.typography import Typography
from django_resaas.saas.models.document import Document, DocumentType
from django_resaas.hr.models.employee import Employee
from django_resaas.hr.models.job_position import JobPosition

pytestmark = pytest.mark.django_db

MODELS_WITH_EXPLICIT_LIST_ROUTE = [
    User, Entity, Address, AuditLog, AnimationSetting, App, LayoutSetting,
    ThemeSurface, Theme, Person, Typography, Document, DocumentType,
    Employee, JobPosition,
]


@pytest.mark.parametrize("Model", MODELS_WITH_EXPLICIT_LIST_ROUTE)
def test_list_route_matches_model_not_add_route(Model):
    routes = ResaasSchemaBuilder(Model=Model).build_routes()

    # a naming convention do 'add'/'view'/'change' já existentes deste
    # model (com ou sem underscore, ex. "add_animation_setting") é a
    # fonte da verdade - o bug era 'list' == 'add' (valor duplicado),
    # não um desvio da convenção model_name do Django.
    assert routes["list"] == "list_" + routes["add"].removeprefix("add_")
    assert routes["list"] != routes["add"]

"""The form a request gets: the latest published layer of each level that
applies - PLATFORM (the database, else the module's forms.py) -> the Entity's
ENTITY TYPE -> the ENTITY -> the BRANCH - merged (merge.py) and validated
again before it is served."""
from django_resaas.saas.core.forms.definition import validate_definition
from django_resaas.saas.core.forms.merge import merge
from django_resaas.saas.core.forms.registry import code_form


class FormNotFound(LookupError):
    pass


def _latest(key, **scope):
    from django_resaas.saas.models.form_definition import FormDefinition

    return (
        FormDefinition.objects.filter(key=key, status=FormDefinition.STATUS_PUBLISHED, **scope)
        .order_by("-version").first()
    )


def layers(key, *, entity_id=None, branch_id=None):
    """[(level, version or "code", definition)] that apply, most general first."""
    from django_resaas.saas.models.entity import Entity
    from django_resaas.saas.models.form_definition import FormDefinition as F

    found = []
    platform = _latest(key, level=F.LEVEL_PLATFORM)
    if platform is not None:
        found.append((F.LEVEL_PLATFORM, platform.version, platform.definition))
    else:
        shipped = code_form(key)
        if shipped is not None:
            found.append((F.LEVEL_PLATFORM, "code", shipped))

    entity = Entity.objects.filter(id=entity_id).only("id", "entity_type_id").first() if entity_id else None
    if entity is not None and entity.entity_type_id:
        row = _latest(key, level=F.LEVEL_ENTITY_TYPE, entity_type_id=entity.entity_type_id)
        if row is not None:
            found.append((F.LEVEL_ENTITY_TYPE, row.version, row.definition))
    if entity is not None:
        row = _latest(key, level=F.LEVEL_ENTITY, entity_id=entity.id)
        if row is not None:
            found.append((F.LEVEL_ENTITY, row.version, row.definition))
        if branch_id:
            row = _latest(key, level=F.LEVEL_BRANCH, entity_id=entity.id, branch_id=branch_id)
            if row is not None:
                found.append((F.LEVEL_BRANCH, row.version, row.definition))
    return found


def resolve(key, *, entity_id=None, branch_id=None):
    """{"definition", "layers": [{level, version}]} - FormNotFound when no
    layer defines the key (a base layer - platform or code - is required:
    lower layers only customise)."""
    found = layers(key, entity_id=entity_id, branch_id=branch_id)
    if not found or found[0][0] != "platform":
        raise FormNotFound(key)
    definition = validate_definition(merge([definition for _, _, definition in found]))
    return {"definition": definition, "layers": [{"level": level, "version": version} for level, version, _ in found]}

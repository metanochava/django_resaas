from rest_framework import serializers
from rest_framework.relations import ManyRelatedField, RelatedField


class TenantRelationsMixin:
    """
    Backend half of the relation picker's tenant isolation: a relation field
    may only be assigned an object of the CURRENT Entity, whatever the client
    sends. The picker's search is already tenant-scoped, but that is only UX -
    a hand-written request could still post another Entity's id.

    This is the generic form of the check several hr serializers already
    wrote by hand (same message, same field attribution - the relation
    querysets stay unscoped on purpose so the error lands on the right field
    instead of the object just vanishing from the choices). Those checks keep
    working unchanged; every other BaseSerializer now gets it for free.

    Applies to every relation in the validated data whose related object
    carries an `entity` (BaseModel) - Entity-less models (Person, User,
    Group, ...) keep their own conventions, and a shared row (entity=NULL) is
    allowed. Without an authenticated tenant context (management commands,
    services calling a serializer directly) nothing is checked.

    Scope is the Entity, not the Branch: Branch scoping is the API's default
    for listing, but same-Entity cross-branch references are legitimate
    (transfers, managers), and Entity isolation is the hard invariant.
    """

    tenant_relation_message = "Does not belong to the current entity."

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get("request")
        entity_id = getattr(request, "entity_id", None)

        if not entity_id:
            return attrs

        errors = {}

        for name, field in self.fields.items():
            if name not in attrs or field.read_only:
                continue

            relation = field.child_relation if isinstance(field, ManyRelatedField) else field

            if not isinstance(relation, RelatedField):
                continue

            related = attrs[name]
            objects = related if isinstance(related, (list, tuple, set)) else [related]

            for obj in objects:
                obj_entity_id = getattr(obj, "entity_id", None)

                # not a tenant object (no entity attr) or a shared row
                if obj is None or not hasattr(obj, "entity_id") or obj_entity_id is None:
                    continue

                if str(obj_entity_id) != str(entity_id):
                    errors[name] = self.tenant_relation_message
                    break

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
